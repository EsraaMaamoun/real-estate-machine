"""
inspect_pkl.py — look inside a .pkl file without opening it in an editor.

    python scripts/inspect_pkl.py                     list every file in Models/
    python scripts/inspect_pkl.py regressor.pkl       open one of them
    python scripts/inspect_pkl.py --all               open all of them

What a .pkl actually is
-----------------------
It is not code. It is a Python object frozen to disk: the fitted numbers a model
learned — split points inside trees, the scaler's means and standard deviations,
the encoder's zipcode-to-price map. Opening one in Notepad shows binary noise;
opening one in Word and saving would destroy it.

Pickle stores a class by its IMPORT PATH, not its source. `regressor.pkl` says,
in effect, "I am a sklearn Pipeline whose second step is a
GradientBoostingRegressor, and here are its learned numbers" — so Python has to
be able to import those classes before it can rebuild the object. That is why
app/preprocessing.py must stay where it is: SmoothedTargetEncoder is referenced
by path from inside several of these files.

So: the code lives in app/*.py, src/*.py and the notebooks. This script shows
what the saved object *is* and what it *learned*.

Security note: never unpickle a file you did not create. Loading a pickle can
run arbitrary code, which is why the format is fine for your own models and
wrong for anything downloaded.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "Models"

sys.path.insert(0, str(ROOT / "app"))  # so SmoothedTargetEncoder can be imported
warnings.filterwarnings("ignore")

INDENT = "  "


def preview(value, width: int = 68) -> str:
    """One readable line for any value."""
    if isinstance(value, float):
        return f"{value:,.4f}"
    if isinstance(value, np.ndarray):
        return f"ndarray shape={value.shape} dtype={value.dtype}"
    if isinstance(value, dict):
        keys = list(value)[:4]
        more = f", +{len(value) - 4} more" if len(value) > 4 else ""
        return f"dict({len(value)} entries: {', '.join(map(str, keys))}{more})"
    if isinstance(value, (list, tuple)):
        text = ", ".join(str(v) for v in value[:6])
        more = f", +{len(value) - 6} more" if len(value) > 6 else ""
        return f"{type(value).__name__}[{len(value)}]: {text}{more}"
    text = str(value).replace("\n", " ")
    return text if len(text) <= width else text[: width - 3] + "..."


def describe_estimator(obj, indent: str = INDENT) -> None:
    """Print what an sklearn object is and the settings it was built with."""
    print(f"{indent}class      : {type(obj).__name__}")
    print(f"{indent}from       : {type(obj).__module__}")

    if hasattr(obj, "steps"):  # Pipeline
        print(f"{indent}pipeline   : {len(obj.steps)} steps")
        for name, step in obj.steps:
            print(f"{indent}{INDENT}{name:<10} -> {type(step).__name__}")

    if hasattr(obj, "transformers"):  # ColumnTransformer
        print(f"{indent}transformers:")
        for name, trans, cols in obj.transformers:
            n = len(cols) if hasattr(cols, "__len__") else "?"
            print(f"{indent}{INDENT}{name:<6} {type(trans).__name__:<22} on {n} columns")

    # The hyperparameters YOU chose (or a grid search chose), not learned values.
    inner = obj.steps[-1][1] if hasattr(obj, "steps") else obj
    if hasattr(inner, "get_params"):
        defaults = type(inner)().get_params() if _constructible(inner) else {}
        chosen = {k: v for k, v in inner.get_params(deep=False).items()
                  if k in defaults and repr(v) != repr(defaults[k])
                  and str(v) != "deprecated"}
        if chosen:
            print(f"{indent}settings   : (only those changed from sklearn's defaults)")
            for k, v in sorted(chosen.items()):
                print(f"{indent}{INDENT}{k:<20} = {preview(v)}")

    # What it learned during .fit() — sklearn's convention is a trailing underscore.
    learned = [a for a in ("n_features_in_", "feature_names_in_", "n_estimators_",
                           "classes_", "cluster_centers_", "inertia_", "n_iter_",
                           "mean_", "scale_", "coef_", "intercept_", "prior_",
                           "feature_importances_")
               if hasattr(inner, a)]
    if learned:
        print(f"{indent}learned    : (produced by .fit — this is the model itself)")
        for a in learned:
            print(f"{indent}{INDENT}{a:<20} = {preview(getattr(inner, a))}")


def _constructible(estimator) -> bool:
    try:
        type(estimator)()
        return True
    except Exception:
        return False


def describe_dict(obj: dict, indent: str = INDENT) -> None:
    print(f"{indent}A plain dictionary — settings and results, no model inside.")
    print(f"{indent}{len(obj)} keys:")
    for k, v in obj.items():
        print(f"{indent}{INDENT}{str(k):<22} {preview(v)}")


def inspect(path: Path) -> None:
    print()
    print("=" * 76)
    print(f"{path.name}   ({path.stat().st_size / 1024:,.1f} KB)")
    print("=" * 76)

    try:
        obj = joblib.load(path)
    except Exception as exc:  # noqa: BLE001
        print(f"{INDENT}Could not load: {type(exc).__name__}: {exc}")
        print(f"{INDENT}If this mentions a missing module, run the script from the")
        print(f"{INDENT}project folder so app/preprocessing.py can be imported.")
        return

    if isinstance(obj, dict):
        describe_dict(obj)
    elif hasattr(obj, "get_params") or hasattr(obj, "steps"):
        describe_estimator(obj)
    elif isinstance(obj, np.ndarray):
        print(f"{INDENT}numpy array, shape {obj.shape}, dtype {obj.dtype}")
        print(f"{INDENT}first values: {np.ravel(obj)[:5]}")
    else:
        print(f"{INDENT}type: {type(obj).__name__}")
        print(f"{INDENT}{preview(obj, 200)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Look inside the project's .pkl files.")
    ap.add_argument("name", nargs="?", help="a file in Models/, e.g. regressor.pkl")
    ap.add_argument("--all", action="store_true", help="inspect every .pkl in Models/")
    args = ap.parse_args(argv)

    if not MODELS.exists():
        raise SystemExit(f"No Models/ folder at {MODELS}")

    files = sorted(MODELS.glob("*.pkl"))

    if args.all:
        for f in files:
            inspect(f)
        return 0

    if args.name:
        target = MODELS / args.name
        if not target.exists():
            raise SystemExit(f"{args.name} not found in Models/. "
                             f"Available: {', '.join(f.name for f in files)}")
        inspect(target)
        return 0

    # No arguments: the menu.
    print(f"\n{len(files)} model files in Models/\n")
    print(f"  {'file':<26}{'size':>10}   what it holds")
    print("  " + "-" * 72)
    known = {
        "regressor.pkl": "the price model — preprocessing + gradient boosting",
        "regressor_config.pkl": "its settings, test scores and known weaknesses",
        "cluster_pipeline.pkl": "the market-segment clustering (K-Means, k=4)",
        "cluster_config.pkl": "segment names and the features used",
        "cluster_scaler.pkl": "the scaler fitted for clustering",
        "kmeans.pkl": "the bare K-Means model",
        "classifier.pkl": "predicts which segment a house belongs to",
        "classifier_config.pkl": "its settings and scores",
        "preprocessor.pkl": "feature scaling + zipcode/city target encoding",
        "scaler.pkl": "the numeric scaler alone",
        "feature_config.pkl": "which features the model uses, in order",
        "reference_stats.pkl": "known zipcodes, price percentiles — used for warnings",
        "shap_background.pkl": "sample used to explain a single house",
        "segment_intervals.pkl": "confidence range per market segment",
        "regression_baseline.pkl": "the Ridge baseline, kept for comparison",
        "regression_config.pkl": "the baseline's settings",
    }
    for f in files:
        print(f"  {f.name:<26}{f.stat().st_size / 1024:>8,.1f} KB   "
              f"{known.get(f.name, '')}")
    print(f"\n  Open one:   python scripts/inspect_pkl.py regressor.pkl")
    print(f"  Open all:   python scripts/inspect_pkl.py --all\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
