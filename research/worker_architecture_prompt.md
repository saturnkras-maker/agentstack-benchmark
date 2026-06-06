Работай на русском. Ты — technical architecture subagent для нового продукта AgentStack Benchmark: публичный сервис для benchmark целых AI agents.

Продуктовая идея:
- Users submit agent manifest + adapter.
- Runner executes standardized tasks in sandbox.
- System collects traces, metrics, costs, errors, repeatability.
- Public leaderboard + agent pages + compare mode.
- Free basic tests, paid deep reports/private runs later.

Ограничения:
- Только analysis. Никаких внешних side effects, регистраций, платежей, сообщений.
- Не использовать секреты/приватные данные.

Верни Markdown:
# Technical MVP architecture
## Самый маленький vertical slice
## Recommended stack
Backend, DB, queue, runner, frontend, auth, deployment.
## Core services
## Data model outline
Tables/entities.
## API contract outline
Endpoints and request/response ideas.
## Runner adapters
HTTP, CLI, Docker; MCP later.
## Sandbox/security boundaries
## Trace storage and evaluation pipeline
## Frontend pages
## 4-6 week phased roadmap
## Risks and deferred choices
Практично, без overengineering.