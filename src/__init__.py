"""
src — the reproducible parts of the Real Estate Machine.

Notebooks/ is the record of how the model was chosen: the experiments, the
comparisons, the reasoning an examiner asks about. This package is how the
result is rebuilt:

    python -m src.train            evaluate the pipeline, write nothing
    python -m src.train --save     rebuild Models/*.pkl from Data/data_clean.csv
    python -m src.train --tune     re-derive the hyperparameters from scratch

The feature engineering itself lives in app/preprocessing.py and is imported
from there, not duplicated here — pickle records a class by its import path, so
a second copy of SmoothedTargetEncoder would produce model files the Streamlit
app could not load.
"""
