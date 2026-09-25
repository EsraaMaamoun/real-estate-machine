# Deployment

Everything needed to turn `app/app.py` into a URL, in the order it has to happen.
Work through it top to bottom; each section ends with a check you can actually see.

**Deliverables:** a live app URL, a public Kaggle notebook, and a
60-second screen recording of the demo.

---

## 0. Before you touch GitHub — the five-minute audit

Run `Notebooks/12_deployment.ipynb` first. It checks, in code:

- every model file the app needs exists,
- nothing secret is about to be committed,
- the requirements list matches what the app actually imports,
- the app starts and values a house without a browser.

Do not skip to section 2 because the app works on your laptop. It works on your
laptop because your laptop has your `.env`, your `venv`, and your `Models/` folder.
The cloud has none of those.

---

## 1. The repository layout that gets deployed

```
Graduation Project/
├── app/
│   ├── app.py                 the app Streamlit runs
│   ├── charts.py              the driver chart
│   ├── explain.py             evidence layer
│   ├── llm_explain.py         language layer
│   ├── preprocessing.py       features — the same file that trained the model
│   └── requirements.txt       what the CLOUD installs (not the project one)
├── Models/                    the six .pkl files the app loads — MUST be committed
├── Data/
│   ├── data_clean.csv         needed by the "Test it on real sales" tab
│   └── split_indices.csv      so that tab draws from the test set only
├── Notebooks/                 01–12, the story
├── reports/                   figures and the business report
├── requirements.txt           the full project environment (for humans, not the cloud)
├── .gitignore
├── .env.example               shows what .env should contain, holds no key
└── DEPLOY.md                  this file
```

**The six `.pkl` files the app loads must be in the repository.** `.gitignore` keeps
exactly those and ignores every other file in `Models/` and `Data/`; section 1 of
notebook 12 lists them and fails if one is ignored. They total under 2 MB. The app has
no way to retrain, and Streamlit Cloud will not run your notebooks. One of them,
`segment_intervals.pkl`, does not crash the app when missing — the app quietly falls
back to the global range, so the live numbers would differ from your local ones.

**`.env` must not be.** See section 3.

---

## 2. Freeze the requirements — the trimmed list, not `pip freeze`

`pip freeze` in your project venv produces something like 180 lines: jupyter,
ipykernel, seaborn, xgboost, notebook, debugpy. The app imports none of them, and
every one is a package the cloud must install before your app can start.

`app/requirements.txt` is the trimmed list — nine packages, traced from the actual
imports. Section 2 of notebook 12 regenerates it with the exact versions installed
on your machine.

One line in it is not negotiable:

```
scikit-learn==1.7.2
```

`Models/regressor.pkl` was pickled by that version. Unpickle it under a different
one and scikit-learn prints `InconsistentVersionWarning` — it usually still works,
but "usually" is not a property you want in a deployed valuation model. Pin it to
whatever version notebook 12 reports for your machine.

---

## 3. Push to GitHub, with nothing secret in it

```bash
cd path\to\real-estate-machine

git init
git add .
git status          # READ THIS BEFORE COMMITTING
```

In that `git status` output, confirm you do **not** see:

- `.env` — your API key
- `venv/` — hundreds of megabytes of packages
- `reports/llm_cache.json` — harmless, but noisy; commit it deliberately if you
  want the demo to work offline (see section 7)

If either of the first two appears, stop and fix `.gitignore` before committing.
A key pushed to a public repository is compromised the moment it lands there, even
if you delete it in the next commit — the history keeps it, and bots scan for it.
If it happens: revoke the key with the provider, generate a new one, and do not
try to rewrite history to hide it.

```bash
git commit -m "Real Estate Machine — graduation project"
git branch -M main
git remote add origin https://github.com/<your-username>/real-estate-machine.git
git push -u origin main
```

Then **open the repository in a private browser window** and look at it as a
stranger. That is the only reliable way to see what is actually public.

---

## 4. Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. **New app** → pick the repository, branch `main`.
3. **Main file path:** `app/app.py`
4. **Advanced settings → Python version:** `3.12` — the same as your local Python.
   Not 3.10: `shap` needs 3.12 or newer and pandas, numpy and scikit-learn need 3.11
   or newer, so the install fails on 3.10. Section 2 of notebook 12 prints the minimum
   for your exact pins.
5. **Advanced settings → Secrets:** paste, in TOML, whichever key you have:

   ```toml
   GEMINI_API_KEY = "your-key-here"
   # GROQ_API_KEY = "your-key-here"
   # GEMINI_MODEL = "gemini-2.5-flash"
   ```

   `app.py` copies these into the environment at startup, so `llm_explain.py`
   keeps reading `os.getenv` and behaves identically locally and in the cloud.
   There is no cloud-only code path to test separately.
6. **Deploy.** The first build takes a few minutes — it is compiling wheels, not
   hanging.

If the build fails, the log names the package. Almost always it is a version that
has no wheel for the chosen Python version: change the Python version or relax the
pin, then redeploy.

---

## 5. Test the live URL properly

- Open it **on your phone, on mobile data, with the laptop's WiFi off.** That is
  the closest thing to "somebody else's computer" you have. It catches the two
  classic failures at once: a file that only exists on your machine, and a path
  that only works on Windows.
- Value a house. Check that the number matches what your local app gives for the
  same house — same inputs, same model, same answer.
- Open the **Test it on real sales** tab. If it says the data files are missing,
  `Data/data_clean.csv` did not get committed.
- Deliberately break something: pick a waterfront house and confirm the warning
  appears.

Community Cloud puts an app to sleep after inactivity. **Open your URL an hour
before the defence** so it is awake when you present.

---

## 6. Publish on Kaggle

`Notebooks/kaggle_real_estate_machine.ipynb` is a self-contained version of the
whole project: cleaning, segments, model, evaluation, in one notebook that runs
top to bottom on Kaggle's servers.

1. Kaggle → **Datasets → New Dataset** → upload **both** `Data/data_clean.csv` and
   `Data/split_indices.csv`. Title it `wa-house-sales-clean`. Upload the split file too,
   or the notebook makes its own split and its numbers stop matching the rest of the
   project.
2. Kaggle → **Create → New Notebook** → **File → Import Notebook** → upload
   `kaggle_real_estate_machine.ipynb`.
3. **Add Input** → your dataset. The notebook searches `/kaggle/input` first and falls
   back to `../Data`, so the same file runs on Kaggle and at home with no edits.
4. **Run All**, confirm every cell produces output, then **Save Version →
   Save & Run All (Commit)**.
5. **Sharing → Public.** Add a link to the live app in the notebook description,
   and add the Kaggle link to your GitHub README.

---

## 7. The backup plan — the cheapest insurance in the project

**Record the demo.** On Windows: `Win + Alt + R` starts the Game Bar recorder,
same shortcut stops it, and the file lands in `Videos/Captures`. Sixty seconds is
enough: fill the form, press the button, point at the range, point at the drivers,
point at a warning. Watch it once to be sure the text is legible.

**Warm the cache.** `reports/llm_cache.json` stores every explanation the app has
generated. If you value your demo house once before the defence and commit that
file, the app can produce the paragraph with no internet at all. Without a key it
falls back to the deterministic explanation, which also works offline — so there
are two independent ways for the demo to survive a dead network.

**Have the local app running too.** A second terminal with `streamlit run
app/app.py` costs nothing and does not depend on anyone else's servers.

---

## Deployment checklist

- [ ] Notebook 12 runs clean, all checks pass
- [ ] `app/requirements.txt` regenerated with exact versions
- [ ] `git status` shows no `.env` and no `venv/`
- [ ] Repository public, checked in a private browser window
- [ ] The six `Models/*.pkl` files and `Data/data_clean.csv` visible on GitHub
- [ ] App deployed, main file `app/app.py`, Python 3.12
- [ ] API key in Streamlit Secrets, not in the repository
- [ ] Live URL opens on your phone over mobile data
- [ ] A valuation on the live app matches the local one
- [ ] Kaggle notebook committed and public
- [ ] 60-second screen recording saved somewhere you can reach without WiFi
- [ ] Both links written into the last slide of the deck
