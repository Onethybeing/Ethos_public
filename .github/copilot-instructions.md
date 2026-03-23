# EthosNews Coding Guidelines

You are working on the **EthosNews** project. Follow these guidelines strictly for all code generation and modifications.

## 1. Architectural Integrity & Modularity
- **Modular Design**: Break down functionality into small, single-purpose modules. Avoid monolithic files.
- **Microservices-ready**: Structure the backend (FastAPI) to be easily splittable into microservices if needed (e.g., separate ingestion, retrieval, verification).
- **Consistency**: Maintain consistent file naming (snake_case for Python, camelCase/PascalCase for JS/React) and directory structures.

## 2. Configuration Management
- **Centralized Configuration**: ALL configuration (API keys, database URLs, feature flags, LLM settings) MUST be defined in a central `config.py` file (or `config/` module) using Pydantic `BaseSettings` or similar typed configuration.
- **Environment Variables**: Use `.env` files for secrets, loaded via the central config. NEVER hardcode secrets in code.
- **LLM Configuration**: Define model parameters (temperature, model name, max tokens) in the central config, not scattered across agent files.

## 3. Code Quality & Standards
- **Type Hinting**: Use strict typing (Python type hints, TypeScript interfaces) for all function signatures and data models.
- **Documentation**: Include docstrings for all modules, classes, and public functions.
- **Error Handling**: Use structured error handling and logging (not just `print` statements).
- **Clean Code**: Follow PEP 8 for Python and standard ESLint/Prettier configs for frontend.

## 4. Project Structure (Ethos Standard)
- `backend/`: FastAPI application
    - `api/`: Routes and endpoints
    - `core/`: Config, security, database connections
    - `services/`: Business logic and agents
    - `models/`: Pydantic/SQLAlchemy models
- `frontend/`: React application (Vite)
