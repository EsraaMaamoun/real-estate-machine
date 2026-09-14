"""
llm_explain.py — the language layer (roadmap Day 11).

What this module is
-------------------
A translator. It receives the dossier that `explain.py` computed — a price, a range,
the SHAP drivers, and the warnings that fired — and returns a paragraph a client can
read. It does not value houses, rank features, or decide whether a valuation looks
sensible. All of that already happened, in code, upstream.

Four defences, because "we called an LLM" is not an engineering answer
---------------------------------------------------------------------
1. **Evidence only.** Every figure the model is allowed to mention is placed in the
   prompt, and the prompt forbids inventing any other. See `build_prompt`.
2. **A grounding check on the output.** `check_grounding` extracts every number from
   the generated text and refuses any that is not in the evidence. This catches the
   one failure mode that matters here — a fluent paragraph containing a made-up
   figure — automatically, rather than hoping a human notices during the demo.
3. **A deterministic fallback.** `fallback_explanation` writes a decent paragraph
   from the same evidence with no API at all. If the key is missing, the network is
   down, the request times out, or the grounding check fails, the app still shows an
   explanation. A demo that crashes because someone else's server is busy is a
   self-inflicted wound.
4. **A cache.** Responses are stored on disk, so the defense demo can run with no
   internet at all.

Configuration (never hard-code a key)
-------------------------------------
Create a file called `.env` in the project root — `.gitignore` already excludes it:

    GEMINI_API_KEY=your-key-here
    # or
    GROQ_API_KEY=your-key-here

    # optional, if the default model name has been retired by the provider
    GEMINI_MODEL=gemini-2.5-flash
    GROQ_MODEL=llama-3.3-70b-versatile

Model names change. Run `python app/llm_explain.py --list-models` to ask the provider
which names your key can actually use, and put a current one in `.env`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv is in requirements.txt, but do not die without it
    pass

CACHE_PATH = Path(__file__).resolve().parent.parent / "reports" / "llm_cache.json"
TIMEOUT_S = 20

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Shared with both providers, and printed alongside the prompt in Notebook 10
# section 6 so "temperature 0.2" is something you can actually point to, not
# just a claim in a markdown table.
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 400

SYSTEM_RULES = """You explain house valuations produced by a statistical model to a
non-technical client. You are a writer, not an appraiser.

Rules, all of them absolute:
1. Use ONLY the figures given in the evidence below. Never introduce a number that is
   not there - no market averages, no interest rates, no dates, no comparable sales,
   no percentages you worked out yourself.
2. Never claim the valuation is accurate. Report the stated typical error and the
   stated range as what they are: this model's measured performance on houses it had
   not seen.
3. If warnings are listed, they are the most important part of your answer. State each
   one plainly in your own words. Do not soften them and do not skip one.
4. Do not speculate about why a feature matters, beyond what the evidence says.
5. No greeting, no sign-off, no bullet points, no headings, no markdown."""

TASK = """Write 110-160 words in three short paragraphs:
- what the model values this house at, and the range around it
- the two or three things that pushed the valuation up or down the most
- how much this figure should be trusted, including every warning listed

Plain British English. Address the reader as "you"."""


# --------------------------------------------------------------------------
# 1. The prompt
# --------------------------------------------------------------------------
def format_evidence(ev: dict) -> str:
    """Render the dossier as flat, unambiguous text. No JSON, no nesting.

    A language model reads a labelled list more reliably than a nested object, and
    a flat list is also what you show an examiner who asks what the AI was told.
    """
    h = ev["house"]
    lines = [
        f"Predicted price: ${ev['predicted_price']:,.0f}",
        f"Honest range (8 out of 10 houses fall in it): ${ev['range_low']:,.0f} to ${ev['range_high']:,.0f}",
        f"Implied price per square foot: ${ev['price_per_sqft']:,.0f}",
        f"Model: {ev['model_name']}",
        f"Typical error of this model on unseen houses: {ev['typical_error_pct']}% (median)",
        f"Share of unseen houses valued within 10% of the true sale price: {ev['within_10pct_of_sale_price']}%",
        "",
        "The house:",
        f"  {h['bedrooms']:g} bedrooms, {h['bathrooms']:g} bathrooms, "
        f"{h['sqft_living']:,} sqft of living space",
        f"  lot {h['sqft_lot']:,} sqft, {h['floors']:g} floor{'' if h['floors'] == 1 else 's'}, "
        f"condition rated {h['condition']} of 5, view rated {h['view']} of 4",
        f"  built in {h['yr_built']} ({ev['house_age']} years old), {h['city']}, zip code {h['zipcode']}",
    ]
    if ev.get("segment"):
        line = f"Market segment: {ev['segment']}"
        if ev.get("segment_typical_error_pct"):
            line += f" (typical error for this segment: {ev['segment_typical_error_pct']}%)"
        lines += ["", line]

    lines += ["", "What moved this valuation, largest first "
                  "(percentages are this feature's effect on the price):"]
    for d in ev["drivers"]:
        sign = "raised" if d["pct_effect"] >= 0 else "lowered"
        lines.append(f"  {d['label']} = {d['value']}: {sign} the valuation by "
                     f"{abs(d['pct_effect'])}%")

    if ev["flags"]:
        lines += ["", "WARNINGS that must appear in your answer:"]
        lines += [f"  - {f}" for f in ev["flags"]]
    else:
        lines += ["", "No warnings were triggered for this house."]
    return "\n".join(lines)


def build_prompt(ev: dict) -> str:
    return f"{SYSTEM_RULES}\n\nEVIDENCE\n--------\n{format_evidence(ev)}\n\nTASK\n----\n{TASK}"


# --------------------------------------------------------------------------
# 2. The grounding check
# --------------------------------------------------------------------------
_NUM = re.compile(r"\$?\s?(\d[\d,]*(?:\.\d+)?)\s?([km])?", re.IGNORECASE)


def allowed_numbers(ev: dict) -> list[float]:
    """Every quantity the model is permitted to state."""
    h = ev["house"]
    vals = [
        ev["predicted_price"], ev["range_low"], ev["range_high"], ev["price_per_sqft"],
        ev["typical_error_pct"], ev["within_10pct_of_sale_price"], ev["house_age"],
        h["bedrooms"], h["bathrooms"], h["sqft_living"], h["sqft_lot"], h["floors"],
        h["condition"], h["view"], h["yr_built"], float(h["zipcode"]),
        8, 10, 4, 5, 100,  # "8 out of 10", "within 10%", the rating scales
    ]
    if ev.get("segment_typical_error_pct"):
        vals.append(ev["segment_typical_error_pct"])
    vals += [abs(d["pct_effect"]) for d in ev["drivers"]]
    vals += [v for f in ev["flags"] for v in _parse_numbers(f)]
    return [float(v) for v in vals if v is not None]


def _parse_numbers(text: str) -> list[float]:
    out = []
    for raw, suffix in _NUM.findall(text):
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if suffix and suffix.lower() == "k":
            v *= 1_000
        elif suffix and suffix.lower() == "m":
            v *= 1_000_000
        out.append(v)
    return out


def check_grounding(text: str, ev: dict, tol: float = 0.02) -> tuple[bool, list[float]]:
    """Is every number in the generated text one we gave it?

    A number counts as grounded if it is within `tol` (relative) of an allowed value,
    which lets the model round $487,300 to $487,000 without being punished for it.
    Returns (ok, list of ungrounded numbers).
    """
    allowed = allowed_numbers(ev)
    bad = []
    for v in _parse_numbers(text):
        if not any(abs(v - a) <= max(tol * abs(a), 0.5) for a in allowed):
            bad.append(v)
    return (len(bad) == 0), bad


# --------------------------------------------------------------------------
# 3. The fallback — no API, no network, still an explanation
# --------------------------------------------------------------------------
def fallback_explanation(ev: dict) -> str:
    """A written explanation assembled from the same evidence, with no model call.

    This is not a placeholder. It is what the app shows whenever the API is
    unavailable or the grounding check fails, so it has to read like something you
    would be willing to put in front of a client.
    """
    h = ev["house"]
    up = [d for d in ev["drivers"] if d["pct_effect"] > 0][:2]
    down = [d for d in ev["drivers"] if d["pct_effect"] < 0][:2]

    def phrase(items, verb):
        if not items:
            return ""
        parts = [f"{d['label']} ({d['value']}), {verb} it by about {abs(d['pct_effect'])}%"
                 for d in items]
        return " and ".join(parts) if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]

    p1 = (f"The model values this {h['bedrooms']:g}-bedroom, {h['sqft_living']:,} sqft house in "
          f"{h['city']} ({h['zipcode']}) at ${ev['predicted_price']:,.0f}, or about "
          f"${ev['price_per_sqft']:,.0f} per square foot. Eight out of ten houses like it fall "
          f"between ${ev['range_low']:,.0f} and ${ev['range_high']:,.0f}, and that range is the "
          f"figure to work with rather than the single number.")

    bits = []
    if up:
        bits.append("What pushed the valuation up: " + phrase(up, "raising") + ".")
    if down:
        bits.append("What pulled it down: " + phrase(down, "lowering") + ".")
    p2 = " ".join(bits) if bits else "No single feature dominated this valuation."
    if ev.get("segment"):
        p2 += f" This house falls into the {ev['segment']} segment of the market."

    p3 = (f"On houses it had never seen, this model was typically {ev['typical_error_pct']}% away "
          f"from the actual sale price, and it landed within 10% of the sale price "
          f"{ev['within_10pct_of_sale_price']}% of the time. It is a screening tool, not a formal "
          f"valuation.")
    if ev.get("segment_typical_error_pct"):
        p3 += (f" For the {ev['segment']} segment specifically, the typical error is "
               f"{ev['segment_typical_error_pct']}%.")
    if ev["flags"]:
        p3 += " Please note: " + " ".join(ev["flags"])

    return "\n\n".join([p1, p2, p3])


# --------------------------------------------------------------------------
# 4. The providers
# --------------------------------------------------------------------------
def _gemini(prompt: str, key: str, timeout: int) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    r = requests.post(
        url,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": TEMPERATURE, "maxOutputTokens": MAX_OUTPUT_TOKENS}},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _groq(prompt: str, key: str, timeout: int) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "temperature": TEMPERATURE, "max_tokens": MAX_OUTPUT_TOKENS,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def available_provider() -> str | None:
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    return None


def list_models() -> None:
    """Ask the provider which model names this key may use. Names change; keys do not."""
    if os.getenv("GEMINI_API_KEY"):
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                         headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=TIMEOUT_S)
        r.raise_for_status()
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                print(m["name"].replace("models/", ""))
    elif os.getenv("GROQ_API_KEY"):
        r = requests.get("https://api.groq.com/openai/v1/models",
                         headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                         timeout=TIMEOUT_S)
        r.raise_for_status()
        for m in r.json().get("data", []):
            print(m["id"])
    else:
        print("No API key found in .env (GEMINI_API_KEY or GROQ_API_KEY).")


# --------------------------------------------------------------------------
# 5. The one function the app calls
# --------------------------------------------------------------------------
def _cache_key(ev: dict) -> str:
    h = ev["house"]
    return json.dumps([h[k] for k in sorted(h)], default=str)


def _read_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=1), encoding="utf-8")


def explain_prediction(ev: dict, provider: str = "auto", timeout: int = TIMEOUT_S,
                       use_cache: bool = True) -> dict:
    """Evidence in, explanation out. Never raises, never returns nothing.

    Returns {"text", "source", "grounded", "ungrounded_numbers", "error"} where
    source is one of "cache", "gemini", "groq", "fallback".
    """
    result = {"text": "", "source": "fallback", "grounded": True,
              "ungrounded_numbers": [], "error": None}

    cache = _read_cache() if use_cache else {}
    key = _cache_key(ev)
    if use_cache and key in cache:
        return {**result, **cache[key], "source": "cache"}

    provider = available_provider() if provider == "auto" else provider
    api_key = os.getenv("GEMINI_API_KEY") if provider == "gemini" else os.getenv("GROQ_API_KEY")

    if not provider or not api_key:
        result["error"] = "no API key configured"
        result["text"] = fallback_explanation(ev)
        return result

    prompt = build_prompt(ev)
    try:
        text = (_gemini if provider == "gemini" else _groq)(prompt, api_key, timeout)
    except Exception as exc:                      # network, quota, bad model name, anything
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["text"] = fallback_explanation(ev)
        return result

    if not text.strip():
        # A reasoning model can spend its whole token budget "thinking" and
        # return empty content with finish_reason "length". check_grounding
        # would call that grounded (no numbers to be wrong), which would show
        # a blank explanation instead of falling back. Treat empty as failure.
        result["error"] = "empty response from provider"
        result["text"] = fallback_explanation(ev)
        return result

    ok, bad = check_grounding(text, ev)
    if not ok:
        # The model wrote a number we did not give it. Do not show it to a client.
        result.update(error="ungrounded numbers in LLM output", grounded=False,
                      ungrounded_numbers=bad, text=fallback_explanation(ev))
        return result

    result.update(text=text, source=provider, grounded=True)
    if use_cache:
        cache[key] = {"text": text, "source": provider, "grounded": True}
        _write_cache(cache)
    return result


if __name__ == "__main__":
    import sys
    if "--list-models" in sys.argv:
        list_models()
    else:
        print("Usage: python app/llm_explain.py --list-models")
