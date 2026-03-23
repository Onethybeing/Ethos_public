# Ethos

## Development with uv

This repository now uses `uv` for Python dependency management.

### 1) Install dependencies

```bash
uv sync
```

This creates `.venv/` and installs dependencies from `pyproject.toml` and `uv.lock`.

### 2) Run Python commands in the project environment

```bash
uv run python -c "from backend.config import get_settings; print(get_settings().app_name)"
```

### 3) Add new dependencies

```bash
uv add <package-name>
```

Then commit both:
- `pyproject.toml`
- `uv.lock`