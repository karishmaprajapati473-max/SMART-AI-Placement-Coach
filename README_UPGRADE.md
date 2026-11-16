# SMART AI Placement Coach — redesigned working copy

This is an upgrade of the existing project. It keeps the React/Vite frontend, FastAPI backend, SQLite authentication store, Monaco editor and Docker runner.

## Project structure

- `backend/` — FastAPI app, authentication and JSON question bank
- `SMART/frontend/` — React + Vite frontend

## Run on Windows

### 1. Backend

Open PowerShell in the `backend` folder. Create a virtual environment only if `.venv` does not already exist:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Keep Docker Desktop running before using Run or Submit in the editor. The backend health endpoint is `http://127.0.0.1:8000/health`.

### 2. Frontend

Open a second PowerShell terminal:

```powershell
cd .\SMART\frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`).

If the frontend needs a different backend address, copy `.env.example` to `.env` and edit `VITE_API_BASE_URL`.

## What changed in this upgrade

- Replaced the dark, inconsistent screen styling with a responsive light SaaS-style design system.
- Added a shared navigation shell across the student workspace.
- Redesigned dashboard, coding setup, lesson, practice, editor, sign-in and sign-up screens.
- Replaced generic lesson placeholder copy with topic-specific lesson content for the two question definitions currently in the project.
- Limited active topic selection to questions that actually exist; other curriculum topics are clearly marked as coming soon.
- Made practice and editor screens load question details from the backend.
- Added question-specific starter code for Python, C, C++ and Java for both existing questions.
- Fixed the `sum_two_numbers` question filename so `/questions/sum_two_numbers` and evaluation can locate it.
- Added a backend `requirements.txt` and frontend `.env.example`.

## Current scope limits

This is a redesigned development build, not a claim of production readiness. The included project archive did not contain a model-training notebook, ML dataset or saved model artifact. The current question bank contains only two questions. Progress analytics, token/session-based authentication, broader curriculum content, automated tests, deployment hardening and ML diagnosis remain future work.
