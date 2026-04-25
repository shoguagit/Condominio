# AGENTS.md

## Stack
- Streamlit app with Supabase backend. Dependencies are pinned in `requirements.txt`; there is no `pyproject.toml` or task runner at repo root.
- Main entrypoint is `app.py`. `streamlit_app.py` is only `from app import *` for alternate hosting entrypoints.

## Run
- Create the repo venv and install deps with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- Run the app with `.venv/bin/streamlit run app.py` from the repo root.
- `config/settings.py` calls `load_dotenv()` on import and raises immediately if `SUPABASE_URL` or `SUPABASE_KEY` are missing. Many tests import code that reaches this module, so missing env breaks import-time, not just runtime.
- `SUPABASE_SERVICE_KEY` is optional for normal app usage but required for admin user operations through `repositories/usuario_repository.py` and recommended for maintenance scripts that must bypass RLS.

## Architecture
- `app.py` owns login, optional dev autologin, admin condominio selection, and the post-login shell.
- Protected modules live in `pages/NN_*.py`.
- UI shell lives in `components/`: `header.py` injects global styles and calls `components.sidebar.render_sidebar()`. If you skip `render_header()`, the app loses its intended navigation shell.
- Data access is repository-first: one class per table/domain in `repositories/`, each wrapping Supabase calls and usually decorated with `utils.error_handler.safe_db_operation`.
- `utils/auth.py` centralizes session state. `st.session_state.mes_proceso` is stored in display format (`MM/YYYY`) for the UI; convert with existing formatter/validator helpers before using it as a DB date.

## Page Conventions
- For new protected pages, follow the order documented in `utils/auth.py`: `st.set_page_config(...)`, then `check_authentication()`, then `render_header()`.
- `check_authentication()` can dev-autologin when `CONDOSYS_DEV_AUTOLOGIN=1` and `CONDOSYS_DEV_AUTOLOGIN_EMAIL=<email>` are set. `app.py` and `utils/auth.py` both support this, and the flow is intended for local QA / Playwright.

## Testing
- Use the venv interpreter explicitly. `tests/README.md` documents a real pitfall: `pytest` on `$PATH` may use a different Python than `.venv`, causing false `ModuleNotFoundError` failures.
- Preferred pattern: `.venv/bin/python -m pytest tests/unit -v`.
- Focused example from repo docs: `.venv/bin/python -m pytest tests/unit/test_reportes.py -v`.
- `tests/unit/test_reportes.py` uses `pytest.importorskip("reportlab")`; missing `reportlab` skips that file instead of failing collection.
- E2E browser coverage is in `tests/e2e_modules.py`. It expects the app to already be running and uses `E2E_BASE_URL`, `E2E_EMAIL`, and `E2E_PASSWORD`; run with `python tests/e2e_modules.py` or `pytest tests/e2e_modules.py -v -s`.
- `tests/e2e/test_crud_manual.py` is a direct Supabase CRUD script, not a hermetic test. It mutates real data and requires a populated DB.

## Migrations And Scripts
- There is no verified migration runner in the repo. SQL changes are stored as `.sql` files and are applied manually in Supabase SQL Editor.
- `scripts/INSTRUCCIONES-MIGRACION.md` documents manual application of root `supabase_migration.sql`.
- For BCV payment-rate backfills, use the wrapper, not the system Python: `bash scripts/reprocesar_tasas_pagos_bcv.sh --sync-api --apply`. The wrapper forces the repo `.venv`; the Python script itself warns against running with system `python3`.
- Before the BCV reprocesar script, the repo expects `scripts/fase7_tasas_bcv_dia_migration.sql` to have been applied in Supabase.

## Existing Instructions
- `.cursor/rules/` contains useful architectural intent for this app, but treat it as advisory prose, not executable truth.
- Do not follow `.cursor/rules/git-workflow.md` literally: it tells the assistant to auto-commit and push to `main`, which conflicts with current OpenCode safety rules.

## Functional Docs
- The functional/technical map of the verified business flows lives in `docs/operaciones-administrativas/README.md`.
- Use that folder when you need module-level context before touching auth, master data, finance setup, payments, bank movements, reports, notifications, monthly close, or BCV rate logic.
