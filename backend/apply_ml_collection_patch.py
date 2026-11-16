"""Safely integrate opt-in ML sample collection into the existing FastAPI main.py.

Run from the backend directory. Creates a timestamped main.py backup first.
Only applies changes when all expected anchors are present.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sys

MAIN = Path("main.py")
if not MAIN.is_file():
    raise SystemExit("ERROR: main.py not found. Run this script from the backend folder.")

original = MAIN.read_text(encoding="utf-8")
updated = original

# 1) Import the consent/data-collection helpers after the auth imports.
import_anchor = "    save_coding_attempt,\n)"
import_block = '''    save_coding_attempt,\n)\nfrom ml.data_collection import (\n    ensure_ml_collection_tables,\n    get_ml_consent,\n    set_ml_consent,\n    store_error_candidate,\n)'''
if "from ml.data_collection import" not in updated:
    if import_anchor not in updated:
        raise SystemExit("ERROR: Could not find the auth import block; no changes made.")
    updated = updated.replace(import_anchor, import_block, 1)

# 2) Add request model directly after LoginRequest.
model_anchor = '''class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
'''
model_block = model_anchor + '''

class MLConsentRequest(BaseModel):
    enabled: bool
'''
if "class MLConsentRequest(BaseModel):" not in updated:
    if model_anchor not in updated:
        raise SystemExit("ERROR: Could not find LoginRequest model; no changes made.")
    updated = updated.replace(model_anchor, model_block, 1)

# 3) Ensure consent/sample tables exist after the users table is initialized.
startup_anchor = '''@app.on_event("startup")
def startup_event():
    init_db()
'''
startup_block = '''@app.on_event("startup")
def startup_event():
    init_db()
    ensure_ml_collection_tables()
'''
if "ensure_ml_collection_tables()" not in updated:
    if startup_anchor not in updated:
        raise SystemExit("ERROR: Could not find startup_event/init_db block; no changes made.")
    updated = updated.replace(startup_anchor, startup_block, 1)

# 4) Add authenticated GET/PUT consent endpoints once.
consent_marker = '@app.get("/ml/consent")'
consent_routes = '''

@app.get("/ml/consent")
def read_ml_consent(request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    return {"status": "success", **get_ml_consent(user["id"])}


@app.put("/ml/consent")
def update_ml_consent(payload: MLConsentRequest, request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    result = set_ml_consent(user["id"], payload.enabled)
    return {"status": "success", **result}
'''
if consent_marker not in updated:
    if startup_block not in updated:
        raise SystemExit("ERROR: Startup block missing after patch; no changes made.")
    updated = updated.replace(startup_block, startup_block + consent_routes, 1)

# 5) Store a candidate after diagnosis and before progress-attempt saving.
# The collection helper re-checks opt-in and leaves every label pending human review.
save_anchor = "    # Save the attempt under the authenticated student\n    attempt_id = save_coding_attempt("
collection_block = '''    # Optional ML research collection: only opted-in users are eligible.
    # Samples are sanitized and remain pending human review (no auto-labeling).
    try:
        store_error_candidate(
            user_id=user["id"],
            question_id=submission.question_id,
            language=submission.language,
            topic=question.get("topic", "Unknown"),
            diagnostic_messages=result.get("diagnostic_messages", []),
            code_snippet=submission.code,
            passed=result["passed"],
            total=result["total"],
            personal_values=(user.get("name", ""), user.get("email", "")),
        )
    except Exception as collection_error:
        # Research collection must never break a student's evaluation.
        print(
            f"[ML COLLECTION] Sample collection skipped: {type(collection_error).__name__}",
            flush=True,
        )

    # Save the attempt under the authenticated student
    attempt_id = save_coding_attempt('''
if "store_error_candidate(" not in updated:
    if save_anchor not in updated:
        raise SystemExit("ERROR: Could not find evaluate endpoint's attempt-save block; no changes made.")
    updated = updated.replace(save_anchor, collection_block, 1)

# Syntax-check before writing anything.
try:
    compile(updated, str(MAIN), "exec")
except SyntaxError as exc:
    raise SystemExit(f"ERROR: Patched main.py did not pass syntax check: {exc}. No changes made.")

if updated == original:
    print("No changes needed: ML collection integration appears to already be present.")
    sys.exit(0)

backup = MAIN.with_name(f"main.py.backup-phase2-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
backup.write_text(original, encoding="utf-8")
MAIN.write_text(updated, encoding="utf-8")
print("ML collection integration added successfully.")
print(f"Backup: {backup}")
print("Added: startup table initialization, authenticated GET/PUT consent endpoints, and opt-in sample collection after evaluation diagnosis.")
print("Safety: consent defaults OFF; collection errors do not interrupt evaluation; labels remain pending human review.")
