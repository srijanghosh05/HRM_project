# HRM Project - AI HR Reward System

This Streamlit MVP demonstrates an AI-assisted HR reward system for compensation management.

## Files

- `main.py` - Streamlit dashboard with employee and manager views.
- `auth.py` - Login, signup, hashed passwords, role checks, and session helpers.
- `users.json` - Local user database created on first run with hashed passwords only.
- `model.py` - Reward scoring, K-Means fairness clustering, anomaly detection, and Power BI export logic.
- `data.csv` - Simulated HR dataset.
- `powerbi_reward_export.csv` - Analyzed results ready for Power BI.
- `requirements.txt` - Python package requirements.

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

If using the bundled Codex Python runtime, run:

```powershell
C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m streamlit run main.py
```

## Reward Logic

Total Score = `(0.4 x Attendance) + (0.4 x Performance) + (0.2 x Peer Feedback)`

The app includes automatic badges, bonus recommendations, AI clustering for fair peer-group comparisons, anomaly detection, Power BI export, Canva AI asset placeholders, and motivation-trigger feedback messages.

## Authentication

The login page supports both manager and employee accounts:

- Manager demo: `manager@company.com` / `Manager@123`
- Employee demo: `aarav.sharma@company.com` / `Employee@123`

Managers are redirected to `/manager/dashboard` and employees are redirected to `/employee/dashboard` inside the Streamlit route state. Public signup only creates employee accounts; manager accounts are admin-created only in the local user database.
