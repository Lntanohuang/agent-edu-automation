# Repository Guidelines

## Project Structure & Module Organization
This monorepo contains three primary services:
- `frontend/`: Vue 3 + Vite + TypeScript UI (`src/views`, `src/router`, `src/stores`).
- `backend/`: Spring Boot 3.2 + Java 17 API (`src/main/java/com/edu/platform`, `src/test/java`).
- `ai-service/`: FastAPI + LangChain service (`app/`, `tests/`, `data/`, `scripts/`).

Domain SQL lives in `backend/sql/`. AI legal knowledge assets are in `ai-service/data/`.

## Build, Test, and Development Commands
Run commands from each module directory:
```bash
cd frontend && npm install && npm run dev      # local UI on :3000
cd frontend && npm run build                   # type-check + production build
cd backend && mvn spring-boot:run              # API on :8080
cd backend && mvn test                         # JUnit test suite
cd ai-service && ./start.sh                    # venv setup + run FastAPI on :8000
cd ai-service && ./run_tests.sh -v             # pytest suite (verbose)
cd ai-service && pytest -m "not integration and not slow"
```

## Coding Style & Naming Conventions
- Java: 4-space indentation, `PascalCase` classes, `camelCase` methods/fields, package under `com.edu.platform`.
- Vue/TS: `<script setup lang="ts">`, `PascalCase` view files (for example `LessonPlanGeneratorV2.vue`), `camelCase` variables/stores.
- Python: PEP 8 style, 4-space indentation, `snake_case` functions/modules, add type hints for new public functions.
- Follow existing formatting patterns (no repo-wide formatter config is enforced currently).

## Testing Guidelines
- Backend uses JUnit 5; keep fast unit tests as `*Test` and infra-dependent tests as `*IntegrationTest`.
- Chat is sync-direct by default (v1.0+); MQ consumers/publishers only load when `chat.mq.enabled=true`, so MQ integration tests require explicitly enabling the feature flag + local RabbitMQ (`5672`).
- Some backend integration tests still require local Redis (`6379`).
- AI service uses `pytest` with markers from `pytest.ini`:
  - `integration`: depends on local Ollama/external infra.
  - `slow`: long-running scenarios.
- Frontend currently has no automated test suite; include manual verification steps in PRs.

## Commit & Pull Request Guidelines
Use Conventional Commit style where possible (observed in history), e.g. `feat(multi-agent): ...`, `refactor(prompt): ...`, `docs: ...`.

For PRs, include:
- clear scope (`frontend`, `backend`, `ai-service`, or cross-module),
- linked issue/task,
- commands run for validation,
- screenshots/GIFs for UI changes,
- notes on config or schema changes (`backend/sql/*`, `.env`, service ports).

## Security & Configuration Tips
Never commit real secrets. Keep credentials in environment variables or local `.env` files; treat defaults in `application.yml` as local-only. Avoid committing generated artifacts (`dist/`, `target/`, `node_modules/`, caches, local vector DB files) unless explicitly required.
