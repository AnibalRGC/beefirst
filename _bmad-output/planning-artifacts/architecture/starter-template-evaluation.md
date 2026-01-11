# Starter Template Evaluation

## Primary Technology Domain

API Backend (Python/FastAPI) based on project requirements analysis

## Starter Options Considered

**Standard FastAPI Starters (Rejected):**
- `fastapi-template`, `full-stack-fastapi-template` - Include SQLAlchemy ORM, violating the raw psycopg3 requirement
- Most production starters - Obscure engineering decisions behind abstractions

**Rationale for Rejection:**
The PRD explicitly requires engineering transparency: "We write every line of business logic and data access ourselves." Using a starter would defeat the purpose of demonstrating architectural discipline.

## Selected Approach: Minimal Scaffold

**Rationale for Selection:**
A from-scratch build with Hexagonal Architecture structure demonstrates the exact engineering judgment the evaluator seeks. The project structure itself is a deliverable.

**Initialization Commands:**

```bash
# Create project structure
mkdir -p beefirst/src/{domain,ports,adapters/{repository,smtp},api}
mkdir -p beefirst/tests/{unit,integration,adversarial}
cd beefirst

# Initialize Python environment
python -m venv .venv && source .venv/bin/activate

# Install minimal dependencies
pip install fastapi uvicorn "psycopg[binary]" bcrypt python-dotenv
pip install pytest pytest-cov httpx  # Testing
```

**Architectural Decisions Established:**

**Language & Runtime:**
- Python 3.11+ with type hints throughout
- No runtime type checking (Pydantic only at API boundary)

**Project Structure (Hexagonal):**
```
src/
├── domain/         # Pure business logic, zero framework imports
│   ├── registration.py  # Trust State Machine
│   └── ports.py         # Interface definitions
├── ports/          # Abstract interfaces for infrastructure
├── adapters/       # Infrastructure implementations
│   ├── repository/ # psycopg3 PostgreSQL adapter
│   └── smtp/       # Console-based email simulation
└── api/            # FastAPI routes and request/response models
```

**Testing Framework:**
- pytest with coverage reporting
- Test categories: unit/, integration/, adversarial/
- Fixtures for database isolation

**Build Tooling:**
- Docker Compose for PostgreSQL + API
- Multi-stage Dockerfile for production
- requirements.txt (no Poetry/PDM - simplicity for evaluator)

**Development Experience:**
- uvicorn with hot reload
- pytest-watch for TDD workflow
- Type hints for IDE support

**Note:** Project initialization using these commands should be the first implementation story.
