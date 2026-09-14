# Setup — VS Code on Windows

Do this once. Ten minutes now saves hours later.

---

## 1. Install

| Tool | Where | Note |
|---|---|---|
| Python 3.11 or 3.12 | python.org | **Tick "Add Python to PATH"** on the first install screen. Do **not** use the Microsoft Store version. |
| VS Code | code.visualstudio.com | |
| Git for Windows | git-scm.com | Needed on Day 13 |

**VS Code extensions** (Extensions panel, `Ctrl+Shift+X`):

- Python (Microsoft)
- Jupyter (Microsoft)

---

## 2. Create the virtual environment

Open the project folder in VS Code (`File → Open Folder`), then open a terminal
(`Ctrl+` `` ` ``) and run:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

You know it worked when your terminal prompt starts with `(venv)`.

> **If PowerShell blocks the activate script**, run this once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## 3. Point VS Code at the environment ← the step everyone skips

`Ctrl+Shift+P` → type **Python: Select Interpreter** → choose the one whose path contains
`venv\Scripts\python.exe`.

If you skip this, your notebooks will use the system Python and every `import pandas` will fail
even though you just installed it. When that happens, come back here.

---

## 4. Start Git

```powershell
git init
git add .
git commit -m "Day 1: project setup and data understanding"
```

---

## Folder structure

```
Graduation Project/
├─ Data/
│   ├─ data.dat                 ← raw source (use this one)
│   ├─ data.csv                 ← pre-processed by someone else, reference only
│   ├─ output.csv               ← corrupted copy, ignore
│   ├─ data_raw_parsed.csv      ← Day 1 output
│   └─ data_clean.csv           ← Day 2 output
├─ Notebooks/       01 … 07
├─ Models/          *.pkl
├─ reports/figures/
├─ app/             app.py, requirements.txt
├─ ROADMAP.md
└─ SETUP.md
```

---

## Daily habit

```powershell
venv\Scripts\activate          # every new terminal
git add . && git commit -m "Day N: what I did"
```

Commit at the end of every day. On Day 13 you will need a repo that already has history —
not one file dumped in at the last minute.

---

## Common errors

| Message | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pandas'` | Wrong interpreter — redo step 3 |
| `'python' is not recognized` | Python not on PATH — reinstall with the PATH box ticked |
| `cannot be loaded because running scripts is disabled` | Run the `Set-ExecutionPolicy` command above |
| `FileNotFoundError: ../Data/data.dat` | Open the **project folder** in VS Code, not a single file |
| Notebook shows "Select Kernel" | Click it, choose Python Environments → `venv` |
