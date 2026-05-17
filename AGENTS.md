# Repository Guidelines

## Agent Output Language
- All user-facing conclusions and step-by-step instructions must be written in Chinese.

## Project Structure & Module Organization
NovelForge is split into two main apps:
- `backend/`: FastAPI service. Core code lives in `backend/app/` (`api/`, `services/`, `db/`, `schemas/`), with entrypoints at `backend/main.py` and `backend/run_backend.py`.
- `frontend/`: Electron + Vue 3 + TypeScript app. Main process code is in `frontend/src/main/`, preload code in `frontend/src/preload/`, and UI code in `frontend/src/renderer/src/` (`components/`, `views/`, `stores/`, `services/`).
- `rules/novelforge-engineering-rule.md`: mandatory engineering principles (low coupling, plugin/event-driven design, maintainability).

## Build, Test, and Development Commands
- Backend setup:
  - `cd backend && pip install -r requirements.txt`
  - `python main.py` (runs API on port `54321`)
- Frontend setup:
  - `cd frontend && npm install`
  - `npm run dev` (Electron dev)
  - `npm run dev:web` (web-only dev mode)
- Quality/build:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - Packaging: `npm run build:win` / `build:mac` / `build:linux`

## Coding Style & Naming Conventions
- Frontend formatting is enforced by `.editorconfig` + Prettier: 2 spaces, LF, UTF-8, `singleQuote: true`, `semi: false`, `printWidth: 100`.
- Run `npm run format` before submitting frontend-heavy changes.
- Use TypeScript for Vue `<script>` blocks and keep component/store/service naming explicit (`useXxxStore`, `XxxService`).
- Backend Python should follow clear module boundaries (API -> service -> data layer), with type hints and minimal hard-coded cross-module dependencies.

## Testing Guidelines
- There is no dedicated automated test suite checked in yet. Minimum validation for PRs:
  - run `npm run lint` and `npm run typecheck` in `frontend/`
  - start backend (`python main.py`) and verify affected API/UI flows manually
- When adding tests, prefer:
  - backend: `backend/tests/test_<feature>.py`
  - frontend: `frontend/src/**/__tests__/*.spec.ts`

## Commit & Pull Request Guidelines
- Recent history mixes short Chinese summaries and conventional prefixes (`fix:`, `feature:`). Prefer: `<type>: <brief summary>` (e.g., `fix: correct context sync for chapter update`).
- Keep commits focused and small; avoid unrelated refactors.
- For PRs, include:
  - change summary
  - file-level change list
  - verification steps/results
- For major features/architecture changes, open an Issue for discussion before implementation.
