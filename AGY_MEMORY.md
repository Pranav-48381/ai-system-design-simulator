# AGY_MEMORY: AI System Design Interview Simulator

> [!IMPORTANT]
> **HIGHEST PRIORITY OPERATIONAL DIRECTIVE (Core Objective):**
> 1. Proceed methodically and steadily, step by step.
> 2. Make a HIGH volume of granular, atomic git commits for every individual task or sub-step.
> 3. Never batch multiple tasks into a single commit; each task MUST have its own dedicated descriptive commit.
> 4. Keep the GitHub contribution activity consistently active and green.
> 5. Update AGY_MEMORY.md checklist and status tracker with each task completion.

## 1. Project Architecture Roadmap

### 1.1 System Overview
The **AI System Design Interview Simulator** is an enterprise-grade backend service designed to conduct autonomous, multi-turn, realistic technical system design interviews. The simulator acts as an expert Staff/Principal Engineer interviewer, guiding candidates through standard interview phases, challenging their architectural decisions, evaluating trade-offs, validating capacity calculations, and delivering multi-dimensional scoring against rigorous industry rubrics.

### 1.2 Core Technology Stack
- **Web & API Framework:** FastAPI (Python 3.12+) with async route handlers and lifespan management.
- **Relational Database:** PostgreSQL with async engine via `asyncpg` and `SQLAlchemy 2.0` DeclarativeBase ORM.
- **Database Migrations:** Alembic with async migration runner.
- **Orchestration & State Machine:** LangGraph (`StateGraph`, checkpointers, conditional branching, state reducers).
- **LLM Integration:** LangChain Core / Chat Models (OpenAI, Anthropic, Gemini) with asynchronous token streaming.
- **Data Validation & Settings:** Pydantic v2 & `pydantic-settings`.
- **Real-Time Communication:** FastAPI WebSocket with structured JSON event framing and token streaming backpressure.
- **Test Suite:** Pytest, `pytest-asyncio`, `httpx` (AsyncClient).

### 1.3 System Design Interview State Machine
The interview follows a 6-stage lifecycle orchestrated by a LangGraph StateGraph:
```
[Start Session]
       │
       ▼
[1. Clarification & Requirements] ── (Functional & Non-functional, Constraints)
       │
       ▼
[2. Capacity Estimation & Scale]  ── (QPS, Storage, Bandwidth, Memory calculations)
       │
       ▼
[3. High-Level Architecture]      ── (APIs, Data Flow, Core Microservices/Components)
       │
       ▼
[4. Deep Dive Component Design]   ── (DB Schema, Sharding, Caching, Concurrency)
       │
       ▼
[5. Bottlenecks & Trade-offs]     ── (Failure Modes, SPOFs, Rate Limiting, Resilience)
       │
       ▼
[6. Evaluation & Debrief]         ── (5-Pillar Rubric Scoring & Actionable Feedback)
       │
       ▼
 [End Session]
```

### 1.4 Database Entity Schema Architecture
- **Users / Candidates (`users`):** Account metadata, target level (Mid, Senior, Staff), interview history.
- **Problems (`problems`):** System design prompts (e.g., TinyURL, Distributed Rate Limiter, Chat System, Video Streaming), constraints, solution blueprints.
- **Rubrics (`rubrics` & `rubric_criteria`):** Standard 5-pillar scoring framework (Requirements, Architecture, Data/Storage, Scalability/Fault Tolerance, Communication).
- **Sessions (`interview_sessions`):** Individual interview execution instances, active stage, total duration, selected persona.
- **Messages (`interview_messages`):** Granular conversation history tagged with stage, speaker role (`candidate`, `interviewer`, `system`), token usage.
- **Stage Progress (`stage_progress`):** Time spent, turn count, criteria satisfaction per stage.
- **Artifacts (`architecture_artifacts`):** Whiteboard diagrams, API definitions, schemas, and estimation notes submitted by candidate.
- **Evaluations & Feedback (`evaluations`, `feedback_items`):** Final numerical scores (1-5), strengths, improvement areas, and tailored study recommendations.
- **Checkpoints (`langgraph_checkpoints`):** LangGraph execution state snapshots for resumption and audit.

### 1.5 Real-Time WebSocket Streaming Protocol
- Candidates connect via `ws://.../api/v1/ws/{session_id}`.
- **Inbound Events:** `candidate_message`, `canvas_update`, `request_hint`, `submit_stage`, `ping`.
- **Outbound Events:** `interviewer_token` (streaming tokens), `interviewer_message_end`, `stage_transition`, `evaluation_ready`, `error`, `pong`.

---

## 2. Master Checklist of Atomic Tasks (220 Tasks)

### Module 01: Project Setup, Tooling & Core Config (Tasks 001 - 012)
- [x] **Task 001**: `/.gitignore` - Initialize project `.gitignore` covering Python, venv, IDE, testing, and environment artifacts.
- [x] **Task 002**: `/pyproject.toml` - Define project metadata, build system, dependencies, and formatting/linting configs.
- [x] **Task 003**: `/.env.example` - Define environment configuration template with PostgreSQL, LLM API keys, and app flags.
- [x] **Task 004**: `/app/__init__.py` - Define top-level application package metadata.
- [ ] **Task 005**: `/app/core/__init__.py` - Define core configuration and utilities package.
- [ ] **Task 006**: `/app/core/config.py` - Implement `Settings` class using `pydantic-settings` with environment validation.
- [ ] **Task 007**: `/app/core/logging.py` - Configure structured logging with contextual metadata and log formats.
- [ ] **Task 008**: `/app/core/constants.py` - Define interview stages, candidate seniority levels, and persona constants.
- [ ] **Task 009**: `/app/core/exceptions.py` - Define domain-specific base and specialized exception classes.
- [ ] **Task 010**: `/app/core/security.py` - Implement session token verification and hashing utilities.
- [ ] **Task 011**: `/Dockerfile` - Create multi-stage production-ready Dockerfile for FastAPI runtime.
- [ ] **Task 012**: `/docker-compose.yml` - Configure multi-container orchestration for FastAPI, PostgreSQL, and pgAdmin.

### Module 02: Database Infrastructure & Connection Engine (Tasks 013 - 022)
- [ ] **Task 013**: `/app/db/__init__.py` - Export database engine, session factory, and base classes.
- [ ] **Task 014**: `/app/db/base.py` - Define SQLAlchemy 2.0 `DeclarativeBase` with naming convention conventions.
- [ ] **Task 015**: `/app/db/session.py` - Create async database engine, session maker, and scoped session lifecycle.
- [ ] **Task 016**: `/app/db/mixins.py` - Create reusable timestamp (`created_at`, `updated_at`) and UUID primary key mixins.
- [ ] **Task 017**: `/alembic.ini` - Configure Alembic CLI settings and script directory references.
- [ ] **Task 018**: `/alembic/env.py` - Implement async Alembic migration environment integrating SQLAlchemy metadata.
- [ ] **Task 019**: `/alembic/script.py.mako` - Customize Alembic migration script template for async operations.
- [ ] **Task 020**: `/app/db/deps.py` - Implement FastAPI `get_db` dependency yielding async database sessions.
- [ ] **Task 021**: `/app/db/health.py` - Implement database connection check and ping utility.
- [ ] **Task 022**: `/app/db/utils.py` - Implement transaction management context managers with automatic rollback.

### Module 03: Database Models (SQLAlchemy ORM) (Tasks 023 - 040)
- [ ] **Task 023**: `/app/models/__init__.py` - Consolidate and export all SQLAlchemy ORM models for Alembic discovery.
- [ ] **Task 024**: `/app/models/enums.py` - Define PostgreSQL enum types for stage, status, role, and difficulty.
- [ ] **Task 025**: `/app/models/user.py` - Implement `User` model with email, name, seniority level, and timestamps.
- [ ] **Task 026**: `/app/models/problem.py` - Implement `SystemDesignProblem` model with title, prompt, requirements, and scale targets.
- [ ] **Task 027**: `/app/models/rubric.py` - Implement `EvaluationRubric` and `RubricCriterion` models.
- [ ] **Task 028**: `/app/models/session.py` - Implement `InterviewSession` model tracking user, problem, stage, and duration.
- [ ] **Task 029**: `/app/models/message.py` - Implement `InterviewMessage` model storing turn-by-turn chat history.
- [ ] **Task 030**: `/app/models/stage_progress.py` - Implement `SessionStageProgress` model tracking per-stage timing and status.
- [ ] **Task 031**: `/app/models/architecture_artifact.py` - Implement `CandidateArchitectureArtifact` model for canvas/diagram states.
- [ ] **Task 032**: `/app/models/evaluation.py` - Implement `InterviewEvaluation` model storing total scores and pillar breakdowns.
- [ ] **Task 033**: `/app/models/feedback.py` - Implement `EvaluationFeedbackItem` model storing structured critiques and tips.
- [ ] **Task 034**: `/app/models/checkpointer.py` - Implement LangGraph state checkpoint storage model.
- [ ] **Task 035**: `/alembic/versions/001_initial_schema.py` - Create baseline database migration script for core entities.
- [ ] **Task 036**: `/app/models/audit_log.py` - Implement `SessionAuditLog` model recording state transitions and events.
- [ ] **Task 037**: `/app/models/tag.py` - Implement `ProblemTag` model for classifying systems (e.g. Distributed, Caching).
- [ ] **Task 038**: `/app/models/problem_tag_association.py` - Implement many-to-many relationship between problems and tags.
- [ ] **Task 039**: `/app/models/stage_metric.py` - Implement `StageMetric` model recording latency, turn count, and token usage.
- [ ] **Task 040**: `/alembic/versions/002_add_audit_and_metrics.py` - Migration for audit logs, tags, and stage metrics.

### Module 04: Pydantic Schemas & DTOs (Tasks 041 - 060)
- [ ] **Task 041**: `/app/schemas/__init__.py` - Export all Pydantic schemas and DTOs.
- [ ] **Task 042**: `/app/schemas/common.py` - Implement standard API response wrappers, pagination, and error schemas.
- [ ] **Task 043**: `/app/schemas/user.py` - Implement `UserCreate`, `UserRead`, `UserUpdate` Pydantic schemas.
- [ ] **Task 044**: `/app/schemas/problem.py` - Implement `ProblemCreate`, `ProblemRead`, and `ProblemSummary` schemas.
- [ ] **Task 045**: `/app/schemas/rubric.py` - Implement `RubricCriterionSchema` and `RubricRead` schemas.
- [ ] **Task 046**: `/app/schemas/session.py` - Implement `SessionCreate`, `SessionRead`, and `SessionStatusUpdate` schemas.
- [ ] **Task 047**: `/app/schemas/message.py` - Implement `MessageCreate`, `MessageRead`, and `MessageHistory` schemas.
- [ ] **Task 048**: `/app/schemas/stage.py` - Implement `StageTransitionRequest` and `StageStatusRead` schemas.
- [ ] **Task 049**: `/app/schemas/artifact.py` - Implement `ArtifactCreate`, `ArtifactRead`, and `ArtifactTypeEnum`.
- [ ] **Task 050**: `/app/schemas/evaluation.py` - Implement `EvaluationRead` and `CompetencyScoreSchema` schemas.
- [ ] **Task 051**: `/app/schemas/feedback.py` - Implement `FeedbackReportRead` and `ImprovementTipSchema` schemas.
- [ ] **Task 052**: `/app/schemas/websocket.py` - Implement inbound and outbound WebSocket message payload schemas.
- [ ] **Task 053**: `/app/schemas/stream.py` - Implement `TokenStreamChunk` and `StreamEventTypeEnum` schemas.
- [ ] **Task 054**: `/app/schemas/canvas.py` - Implement `WhiteboardSyncEvent` and `DiagramNodeSchema` schemas.
- [ ] **Task 055**: `/app/schemas/estimation.py` - Implement `EstimationCalculationSchema` and validation result schemas.
- [ ] **Task 056**: `/app/schemas/api_design.py` - Implement `EndpointDesignSchema` and `ParameterSchema` schemas.
- [ ] **Task 057**: `/app/schemas/data_model_design.py` - Implement `TableSchemaDesign` and `RelationSchema` schemas.
- [ ] **Task 058**: `/app/schemas/interview_report.py` - Implement comprehensive interview report DTO schema.
- [ ] **Task 059**: `/app/schemas/persona.py` - Implement `InterviewerPersonaConfigSchema` defining persona traits.
- [ ] **Task 060**: `/app/schemas/health.py` - Implement `HealthCheckResponse` and `ComponentHealthSchema` schemas.

### Module 05: Problem Bank & Seeding Engine (Tasks 061 - 075)
- [ ] **Task 061**: `/app/data/__init__.py` - Package initialization for static seed data and loaders.
- [ ] **Task 062**: `/app/data/problems/url_shortener.json` - System design problem specification for URL Shortener (TinyURL).
- [ ] **Task 063**: `/app/data/problems/rate_limiter.json` - Problem specification for Distributed API Rate Limiter.
- [ ] **Task 064**: `/app/data/problems/notification_service.json` - Problem specification for Multi-Channel Notification Engine.
- [ ] **Task 065**: `/app/data/problems/chat_system.json` - Problem specification for Real-Time Chat System (Slack/WhatsApp).
- [ ] **Task 066**: `/app/data/problems/video_streaming.json` - Problem specification for Global Video Streaming Platform.
- [ ] **Task 067**: `/app/data/problems/metrics_monitoring.json` - Problem specification for Time-Series Metrics & Alerting System.
- [ ] **Task 068**: `/app/data/problems/ecommerce_checkout.json` - Problem specification for High-Concurrency Flash Sale Checkout.
- [ ] **Task 069**: `/app/data/rubrics/standard_rubric.json` - Standard 5-competency evaluation rubric JSON definition.
- [ ] **Task 070**: `/app/data/personas/interviewer_personas.json` - Persona definitions (Collaborative, Rigorous, Socratic).
- [ ] **Task 071**: `/app/services/seeder.py` - Implement database seeder populating problems, rubrics, and default personas.
- [ ] **Task 072**: `/app/scripts/seed_db.py` - CLI script runner for executing database seeder.
- [ ] **Task 073**: `/app/data/loader.py` - Implement JSON problem loader with schema validation.
- [ ] **Task 074**: `/app/data/problems/web_crawler.json` - Problem specification for Distributed Scalable Web Crawler.
- [ ] **Task 075**: `/app/data/problems/collaborative_editor.json` - Problem specification for Real-Time Collaborative Document Editor.

### Module 06: Repositories & Data Access Layer (Tasks 076 - 090)
- [ ] **Task 076**: `/app/repositories/__init__.py` - Export repository classes and interfaces.
- [ ] **Task 077**: `/app/repositories/base.py` - Implement generic async `BaseRepository` with CRUD and pagination.
- [ ] **Task 078**: `/app/repositories/user_repo.py` - Implement `UserRepository` with email query and auth helpers.
- [ ] **Task 079**: `/app/repositories/problem_repo.py` - Implement `ProblemRepository` with difficulty and tag filtering.
- [ ] **Task 080**: `/app/repositories/session_repo.py` - Implement `SessionRepository` with active session state tracking.
- [ ] **Task 081**: `/app/repositories/message_repo.py` - Implement `MessageRepository` with ordered stage retrieval.
- [ ] **Task 082**: `/app/repositories/stage_progress_repo.py` - Implement `StageProgressRepository` for stage metrics.
- [ ] **Task 083**: `/app/repositories/artifact_repo.py` - Implement `ArtifactRepository` for architecture canvas state.
- [ ] **Task 084**: `/app/repositories/evaluation_repo.py` - Implement `EvaluationRepository` for session scorecards.
- [ ] **Task 085**: `/app/repositories/feedback_repo.py` - Implement `FeedbackRepository` for category-based feedback.
- [ ] **Task 086**: `/app/repositories/rubric_repo.py` - Implement `RubricRepository` for scoring rubric retrieval.
- [ ] **Task 087**: `/app/repositories/audit_repo.py` - Implement `AuditRepository` for logging interview events.
- [ ] **Task 088**: `/app/repositories/stage_metric_repo.py` - Implement `StageMetricRepository` for performance analytics.
- [ ] **Task 089**: `/app/repositories/unit_of_work.py` - Implement `UnitOfWork` pattern coordinating multi-repository transactions.
- [ ] **Task 090**: `/app/repositories/deps.py` - Define FastAPI dependencies for repositories and `UnitOfWork`.

### Module 07: LangGraph State Machine & Graph Definitions (Tasks 091 - 105)
- [ ] **Task 091**: `/app/graph/__init__.py` - Export LangGraph components, state definitions, and builder.
- [ ] **Task 092**: `/app/graph/state.py` - Define `InterviewState` TypedDict with channel reducers and message history.
- [ ] **Task 093**: `/app/graph/stages.py` - Implement `InterviewStage` enum, transition logic, and stage prerequisites.
- [ ] **Task 094**: `/app/graph/context.py` - Implement `InterviewContext` utility for extracting stage-specific state.
- [ ] **Task 095**: `/app/graph/checkpointer.py` - Implement Postgres and in-memory checkpointer provider for LangGraph.
- [ ] **Task 096**: `/app/graph/events.py` - Define graph execution event types for WebSocket streaming bridge.
- [ ] **Task 097**: `/app/graph/modifiers.py` - Implement state modifier functions for appending turns and updating stage.
- [ ] **Task 098**: `/app/graph/guards.py` - Implement stage exit criteria guards and turn-limit threshold checks.
- [ ] **Task 099**: `/app/graph/channels.py` - Implement custom LangGraph state channels for artifact and canvas synchronization.
- [ ] **Task 100**: `/app/graph/config.py` - Implement runnable configurations with session and thread metadata.
- [ ] **Task 101**: `/app/graph/types.py` - Define internal typing, intent action schemas, and node result containers.
- [ ] **Task 102**: `/app/graph/serializers.py` - Implement state serialization and deserialization helpers for persistence.
- [ ] **Task 103**: `/app/graph/state_history.py` - Implement checkpoint traversal and stage history reconstructor.
- [ ] **Task 104**: `/app/graph/metrics.py` - Implement node execution timing and token counter metrics collector.
- [ ] **Task 105**: `/app/graph/registry.py` - Implement versioned graph runner registry for dynamic model switching.

### Module 08: Prompt Templates & LLM Engineering (Tasks 106 - 120)
- [ ] **Task 106**: `/app/prompts/__init__.py` - Export prompt templates and builder utilities.
- [ ] **Task 107**: `/app/prompts/base.py` - Implement base system prompt foundation and formatting helpers.
- [ ] **Task 108**: `/app/prompts/personas.py` - Implement persona prompt templates (Socratic, Staff Engineer, Challenging).
- [ ] **Task 109**: `/app/prompts/clarification.py` - Implement prompt templates for functional/non-functional requirements phase.
- [ ] **Task 110**: `/app/prompts/estimation.py` - Implement prompt templates for back-of-the-envelope capacity estimation.
- [ ] **Task 111**: `/app/prompts/architecture.py` - Implement prompt templates for high-level architecture critique.
- [ ] **Task 112**: `/app/prompts/deep_dive.py` - Implement prompt templates for component deep dives and edge cases.
- [ ] **Task 113**: `/app/prompts/bottleneck.py` - Implement prompt templates for bottleneck, SPOF, and resilience analysis.
- [ ] **Task 114**: `/app/prompts/router.py` - Implement intent classification and stage readiness prompt templates.
- [ ] **Task 115**: `/app/prompts/rubric_eval.py` - Implement rubric-aligned scoring prompts for competency evaluation.
- [ ] **Task 116**: `/app/prompts/final_summary.py` - Implement comprehensive interview report generation prompts.
- [ ] **Task 117**: `/app/prompts/hint_generator.py` - Implement progressive 3-tier hint generation prompt templates.
- [ ] **Task 118**: `/app/prompts/diagram_parser.py` - Implement prompt template for parsing candidate Mermaid/text diagrams.
- [ ] **Task 119**: `/app/prompts/math_verifier.py` - Implement prompt template for verifying capacity calculation math.
- [ ] **Task 120**: `/app/prompts/anti_hallucination.py` - Implement grounding and consistency validation prompt guards.

### Module 09: LangGraph Nodes Implementation (Tasks 121 - 140)
- [ ] **Task 121**: `/app/graph/nodes/__init__.py` - Export all graph node handler functions.
- [ ] **Task 122**: `/app/graph/nodes/router_node.py` - Implement router node determining candidate intent and next action.
- [ ] **Task 123**: `/app/graph/nodes/clarification_node.py` - Implement clarification node guiding requirements discovery.
- [ ] **Task 124**: `/app/graph/nodes/estimation_node.py` - Implement estimation node checking scale math and assumptions.
- [ ] **Task 125**: `/app/graph/nodes/architecture_node.py` - Implement high-level architecture node reviewing services and APIs.
- [ ] **Task 126**: `/app/graph/nodes/deep_dive_node.py` - Implement deep dive node challenging storage, caching, and sharding.
- [ ] **Task 127**: `/app/graph/nodes/bottleneck_node.py` - Implement bottleneck node probing failure modes and fault tolerance.
- [ ] **Task 128**: `/app/graph/nodes/interviewer_node.py` - Implement conversational response node blending persona and feedback.
- [ ] **Task 129**: `/app/graph/nodes/hint_node.py` - Implement hint generator node providing subtle, unblocking guidance.
- [ ] **Task 130**: `/app/graph/nodes/stage_evaluator_node.py` - Implement intermediate stage assessment node.
- [ ] **Task 131**: `/app/graph/nodes/final_evaluator_node.py` - Implement final multi-rubric scoring synthesis node.
- [ ] **Task 132**: `/app/graph/nodes/report_node.py` - Implement debrief report generation node.
- [ ] **Task 133**: `/app/graph/nodes/canvas_node.py` - Implement architecture canvas ingestion and evaluation node.
- [ ] **Task 134**: `/app/graph/nodes/timeout_node.py` - Implement stage timeout and pacing enforcement node.
- [ ] **Task 135**: `/app/graph/nodes/error_fallback_node.py` - Implement resilient fallback node for model errors and timeouts.
- [ ] **Task 136**: `/app/graph/edges/__init__.py` - Export conditional routing edge functions.
- [ ] **Task 137**: `/app/graph/edges/conditional_edges.py` - Implement dynamic edge logic for intent-based routing.
- [ ] **Task 138**: `/app/graph/edges/stage_router.py` - Implement stage transition gatekeeper evaluating completion readiness.
- [ ] **Task 139**: `/app/graph/builder.py` - Assemble and compile the full LangGraph `StateGraph`.
- [ ] **Task 140**: `/app/graph/visualizer.py` - Implement Mermaid diagram generation of the compiled graph topology.

### Module 10: LLM Services & Streaming Engine (Tasks 141 - 155)
- [ ] **Task 141**: `/app/services/__init__.py` - Export application service providers.
- [ ] **Task 142**: `/app/services/llm_factory.py` - Implement LLM client factory with multi-provider failover support.
- [ ] **Task 143**: `/app/services/token_streamer.py` - Implement async token streamer yielding real-time chunks.
- [ ] **Task 144**: `/app/services/prompt_service.py` - Implement dynamic prompt assembly and context hydration service.
- [ ] **Task 145**: `/app/services/rate_limit_handler.py` - Implement API exponential backoff and retry policy handler.
- [ ] **Task 146**: `/app/services/cost_tracker.py` - Implement token consumption and operational cost tracking service.
- [ ] **Task 147**: `/app/services/json_extractor.py` - Implement resilient structured JSON extraction from LLM responses.
- [ ] **Task 148**: `/app/services/cache_service.py` - Implement prompt and completion caching service.
- [ ] **Task 149**: `/app/services/diagram_service.py` - Implement Mermaid diagram validation and syntax verification service.
- [ ] **Task 150**: `/app/services/math_service.py` - Implement system design scale unit converter (QPS, IOPS, PB/month).
- [ ] **Task 151**: `/app/services/interview_service.py` - Implement interview session lifecycle orchestrator.
- [ ] **Task 152**: `/app/services/evaluation_service.py` - Implement evaluation report persistence and scorecard compiler.
- [ ] **Task 153**: `/app/services/stage_service.py` - Implement stage progression and time allocation manager.
- [ ] **Task 154**: `/app/services/artifact_service.py` - Implement design artifact versioning and canvas state service.
- [ ] **Task 155**: `/app/services/export_service.py` - Implement interview transcript and scorecard exporter (Markdown & JSON).

### Module 11: Real-Time WebSocket Infrastructure (Tasks 156 - 170)
- [ ] **Task 156**: `/app/websocket/__init__.py` - Export WebSocket connection manager and handlers.
- [ ] **Task 157**: `/app/websocket/connection_manager.py` - Implement active WebSocket connection registry and channel pool.
- [ ] **Task 158**: `/app/websocket/protocol.py` - Implement structured JSON event encoder and decoder.
- [ ] **Task 159**: `/app/websocket/handlers/__init__.py` - Export WebSocket event handlers.
- [ ] **Task 160**: `/app/websocket/handlers/chat_handler.py` - Implement handler for candidate chat turns and streaming responses.
- [ ] **Task 161**: `/app/websocket/handlers/canvas_handler.py` - Implement handler for whiteboard/canvas diagram events.
- [ ] **Task 162**: `/app/websocket/handlers/command_handler.py` - Implement handler for slash commands (`/hint`, `/skip`, `/submit`).
- [ ] **Task 163**: `/app/websocket/handlers/heartbeat_handler.py` - Implement ping-pong keepalive and connection monitoring.
- [ ] **Task 164**: `/app/websocket/broadcaster.py` - Implement pub/sub event dispatcher for session broadcast.
- [ ] **Task 165**: `/app/websocket/stream_adapter.py` - Implement async generator bridging LangGraph stream to WebSocket events.
- [ ] **Task 166**: `/app/websocket/auth.py` - Implement WebSocket ticket and query token authentication validator.
- [ ] **Task 167**: `/app/websocket/rate_limiter.py` - Implement connection-level message rate limiter and flood protector.
- [ ] **Task 168**: `/app/websocket/session_tracker.py` - Implement real-time candidate presence and connection counter.
- [ ] **Task 169**: `/app/websocket/recovery.py` - Implement client reconnection handler with missed event playback.
- [ ] **Task 170**: `/app/websocket/deps.py` - Define FastAPI dependency injection for WebSocket manager and handlers.

### Module 12: FastAPI Routers & API Endpoints (Tasks 171 - 190)
- [ ] **Task 171**: `/app/api/__init__.py` - Export API router.
- [ ] **Task 172**: `/app/api/v1/__init__.py` - Initialize API v1 module.
- [ ] **Task 173**: `/app/api/v1/router.py` - Assemble and mount all v1 route sub-modules.
- [ ] **Task 174**: `/app/api/v1/endpoints/__init__.py` - Export endpoint handlers.
- [ ] **Task 175**: `/app/api/v1/endpoints/health.py` - Implement health check, readiness probe, and system status endpoints.
- [ ] **Task 176**: `/app/api/v1/endpoints/users.py` - Implement user registration, profile retrieval, and seniority update endpoints.
- [ ] **Task 177**: `/app/api/v1/endpoints/problems.py` - Implement system design problem catalog and detail endpoints.
- [ ] **Task 178**: `/app/api/v1/endpoints/sessions.py` - Implement interview session creation, pause, resume, and finish endpoints.
- [ ] **Task 179**: `/app/api/v1/endpoints/messages.py` - Implement paginated message history retrieval endpoints.
- [ ] **Task 180**: `/app/api/v1/endpoints/artifacts.py` - Implement candidate architecture artifact CRUD endpoints.
- [ ] **Task 181**: `/app/api/v1/endpoints/evaluations.py` - Implement evaluation scorecard and debrief retrieval endpoints.
- [ ] **Task 182**: `/app/api/v1/endpoints/rubrics.py` - Implement evaluation rubric listing and criteria detail endpoints.
- [ ] **Task 183**: `/app/api/v1/endpoints/ws.py` - Implement WebSocket interview endpoint with lifecycle connection handling.
- [ ] **Task 184**: `/app/api/v1/endpoints/export.py` - Implement interview session export endpoint (Markdown/JSON download).
- [ ] **Task 185**: `/app/api/v1/endpoints/analytics.py` - Implement candidate aggregate performance analytics endpoints.
- [ ] **Task 186**: `/app/api/deps.py` - Define shared API dependencies (database, current user, validation).
- [ ] **Task 187**: `/app/middleware/__init__.py` - Export HTTP middleware modules.
- [ ] **Task 188**: `/app/middleware/timing.py` - Implement request latency tracking middleware (`X-Process-Time-Ms`).
- [ ] **Task 189**: `/app/middleware/correlation_id.py` - Implement request correlation ID middleware (`X-Correlation-ID`).
- [ ] **Task 190**: `/app/middleware/error_handler.py` - Implement global exception handling middleware with RFC-7807 problem details.

### Module 13: Application Lifecycle & Server Entrypoint (Tasks 191 - 200)
- [ ] **Task 191**: `/app/lifespan.py` - Implement async lifespan context manager managing startup/shutdown hooks.
- [ ] **Task 192**: `/app/main.py` - Create FastAPI application factory mounting CORS, middleware, and routers.
- [ ] **Task 193**: `/run.py` - Create server entrypoint script with Uvicorn CLI configuration.
- [ ] **Task 194**: `/app/cli.py` - Create command-line management interface (seed, test-run, export-rubric).
- [ ] **Task 195**: `/Makefile` - Define developer productivity targets (`dev`, `test`, `lint`, `migrate`, `seed`).
- [ ] **Task 196**: `/README.md` - Write comprehensive project documentation, architecture guide, and setup instructions.
- [ ] **Task 197**: `/scripts/test_ws_client.py` - Create terminal-based interactive WebSocket client for testing interviews.
- [ ] **Task 198**: `/scripts/simulate_interview.py` - Create automated headless end-to-end interview simulation script.
- [ ] **Task 199**: `/scripts/export_rubric_docs.py` - Create script exporting system design rubrics to Markdown.
- [ ] **Task 200**: `/scripts/benchmark_latency.py` - Create benchmarking script measuring LLM token latency and database queries.

### Module 14: Comprehensive Test Suite (Tasks 201 - 220)
- [ ] **Task 201**: `/tests/__init__.py` - Initialize test suite package.
- [ ] **Task 202**: `/tests/conftest.py` - Configure Pytest fixtures for async engine, test client, and mock LLMs.
- [ ] **Task 203**: `/tests/test_config.py` - Implement unit tests for environment settings and validation.
- [ ] **Task 204**: `/tests/test_db_models.py` - Implement database model constraint and relationship tests.
- [ ] **Task 205**: `/tests/test_problem_loader.py` - Implement tests for JSON problem catalog loading and parsing.
- [ ] **Task 206**: `/tests/test_user_repo.py` - Implement CRUD tests for `UserRepository`.
- [ ] **Task 207**: `/tests/test_session_repo.py` - Implement state management tests for `SessionRepository`.
- [ ] **Task 208**: `/tests/test_graph_state.py` - Implement unit tests for LangGraph state mutations and reducers.
- [ ] **Task 209**: `/tests/test_router_node.py` - Implement tests for intent classification and stage transitions.
- [ ] **Task 210**: `/tests/test_clarification_node.py` - Implement tests for requirements gathering node.
- [ ] **Task 211**: `/tests/test_estimation_node.py` - Implement tests for scale math verification node.
- [ ] **Task 212**: `/tests/test_architecture_node.py` - Implement tests for high-level architecture critique node.
- [ ] **Task 213**: `/tests/test_deep_dive_node.py` - Implement tests for component deep dive challenge node.
- [ ] **Task 214**: `/tests/test_evaluator_node.py` - Implement tests for final 5-pillar rubric evaluation node.
- [ ] **Task 215**: `/tests/test_graph_compilation.py` - Implement tests verifying LangGraph topology and valid edge paths.
- [ ] **Task 216**: `/tests/test_api_health.py` - Implement integration tests for health check endpoints.
- [ ] **Task 217**: `/tests/test_api_sessions.py` - Implement integration tests for session creation and lifecycle REST APIs.
- [ ] **Task 218**: `/tests/test_api_problems.py` - Implement integration tests for problem catalog REST APIs.
- [ ] **Task 219**: `/tests/test_ws_streaming.py` - Implement integration tests for WebSocket real-time token streaming.
- [ ] **Task 220**: `/tests/test_full_interview_flow.py` - Implement end-to-end multi-turn interview simulation test.

---

## 3. Current Status Tracker
- **Current Task Pending Execution:** `Task 005 - Define core configuration and utilities package in app/core/__init__.py`
- **Last Executed Task:** `Task 004 - Define top-level application package metadata in app/__init__.py`
- **Total Tasks:** 220
- **Completed Tasks:** 4
- **Remaining Tasks:** 216




