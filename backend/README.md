# Voice2Text Vietnamese - Backend

## Overview

Real-time Vietnamese speech-to-text backend with hate speech detection and content moderation.

## Clean Architecture

This backend follows Clean Architecture principles with 4 distinct layers:

- **Domain Layer**: Pure business entities and logic
- **Application Layer**: Use cases and business workflows  
- **Infrastructure Layer**: Database, workers, external services
- **API Layer**: REST endpoints, WebSocket handlers, middleware

## Quick Start

```bash
# Install dependencies with Poetry
poetry install

# Run development server
poetry run python run.py

# Run tests
poetry run pytest

# Run code quality checks
poetry run black .
poetry run flake8 .
poetry run mypy .
```

## Architecture

See `docs/docs-plan-refactor.md` for detailed architecture documentation.

## Current Status

**Phase 1: Foundation** - Clean Architecture migration in progress.
