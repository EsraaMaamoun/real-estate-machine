"""
design.py — the Ink & Amber design system, in one place.

Every colour here was checked with the data-viz palette validator rather than
chosen by eye:

    light surface #FBFAF7 : amber #C07214, teal #0094A0, brick #B23A20
    dark  surface #191714 : amber #C4822B, teal #1F9BA8, brick #C25940

Both sets pass the lightness band, the chroma floor, colour-vision separation
(worst adjacent pair ΔE 16.5 protan / 14.4 deutan against a floor of 8), the
normal-vision floor and 3:1 contrast against their surface.

AMBER, TEAL and BRICK are the only colours allowed to carry meaning:

    AMBER   the subject of the slide - this model, this house, the answer
    TEAL    a gain, a pass, a thing that helps
    BRICK   a loss, a failure, a thing that costs money

GRAPHITE and STONE are neutral context - the bars a highlighted bar is
compared against. They never mean anything on their own.

The app (`app/charts.py`, `.streamlit/config.toml`) uses the same values, so
the deck and the live demo read as one product.
"""

# --- surfaces and ink ------------------------------------------------------
PAPER = "#FBFAF7"   # slide and app background
CARD = "#F2EFE9"    # a block of related content sitting on paper
CARD_WARM = "#FAF0E2"  # a card that is making a positive point
CARD_COOL = "#F6EEEB"  # a card that is making a negative one
RULE = "#E2DCD1"    # hairlines, axis lines
INK = "#191714"     # headlines, dark slides
BODY = "#3A342C"    # body text on paper
MUTED = "#6B6358"   # captions, axis labels, secondary text

# --- meaning ---------------------------------------------------------------
AMBER = "#C07214"
TEAL = "#0094A0"
BRICK = "#B23A20"

# --- neutral context -------------------------------------------------------
GRAPHITE = "#4A4640"
STONE = "#C9C2B6"
SHADE = "#EFEBE3"   # a band of context behind marks

# --- on the dark slides ----------------------------------------------------
INK_DEEP = "#141210"
INK_CARD = "#2A2621"
AMBER_DARK = "#C4822B"
TEAL_DARK = "#1F9BA8"
BRICK_DARK = "#C25940"
AMBER_TEXT_DARK = "#E8B361"   # small text on ink needs a lighter step
PAPER_DIM = "#D9D2C6"         # body text on ink

# --- type ------------------------------------------------------------------
HEAD = "Cambria"    # serif headlines - both render true-to-width in QA
BODY_FACE = "Calibri"


def apply_matplotlib():
    """Make every figure in this project inherit the system."""
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "font.size": 13,
        "axes.titlesize": 14.5,
        "axes.labelsize": 12.5,
        "axes.edgecolor": RULE,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": False,
    })


def bare(ax, keep=("bottom",)):
    """Strip the frame down to the one line that carries information."""
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)
    ax.grid(False)
