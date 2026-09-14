"""
charts.py — the one drawing the app makes.

Why this is its own module rather than a function inside `app.py`
----------------------------------------------------------------
Notebook 11 wants to show the same chart the app shows. Importing it from `app.py`
would execute the whole app in the notebook's process (Streamlit scripts run on
import), which leaves Streamlit's internal state half-built and breaks the tests
later in that notebook.

So the chart lives here: `app.py` imports it, the notebook imports it, and there is
still only one copy of the drawing code.
"""

from __future__ import annotations

# The diverging pair. One hue for "raised the valuation", one for "lowered it", with
# a neutral axis between them - the honest encoding for a quantity with a natural
# zero. Two hues, never a gradient of many.
UP = "#2a78d6"
DOWN = "#e34948"
AXIS = "#8a8985"
INK = "#52514e"
RULE = "#d8d7d2"


def driver_chart(drivers: list[dict]):
    """Horizontal diverging bars: what moved this valuation, largest first.

    Horizontal because the labels are phrases ("years since it was last renewed") and
    phrases read left to right. Largest at the top, so the eye lands on the biggest
    driver first. The percentage is written on the bar rather than read off a second
    axis, and the gridlines are gone because they would compete with the bars.

    `drivers` is the list `explain.HouseValuer.drivers()` returns.
    """
    import matplotlib.pyplot as plt

    d = list(reversed(drivers))  # matplotlib draws the first item at the bottom
    labels = [f"{x['label']}\n{x['value']}" for x in d]
    values = [float(x["pct_effect"]) for x in d]
    colors = [UP if v >= 0 else DOWN for v in values]

    fig, ax = plt.subplots(figsize=(7, 0.62 * len(d) + 0.9))
    ax.barh(labels, values, color=colors, height=0.62)
    ax.axvline(0, color=AXIS, linewidth=1)

    span = max((abs(v) for v in values), default=1) or 1
    for y, v in enumerate(values):
        ax.text(v + (0.04 * span if v >= 0 else -0.04 * span), y,
                f"{v:+.1f}%", va="center",
                ha="left" if v >= 0 else "right", fontsize=9.5, color=INK)

    ax.set_xlim(-1.45 * span, 1.45 * span)
    ax.set_xlabel("effect on the predicted price", fontsize=9.5, color=INK)
    ax.tick_params(axis="y", labelsize=9.5, length=0)
    ax.tick_params(axis="x", labelsize=9, colors=INK)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.grid(False)
    fig.tight_layout()
    return fig
