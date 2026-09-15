<div align="center">

# Formbrew API

**Build forms through natural language: powered by Groq + FastAPI**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=fff)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=fff)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=fff)](https://postgresql.org)
[![Groq](https://img.shields.io/badge/Groq-000?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIgMkM2LjQ4IDIgMiA2LjQ4IDIgMTJzNC40OCAxMCAxMCAxMCAxMC00LjQ4IDEwLTEwUzE3LjUyIDIgMTIgMnptMCAxOGMtNC40MSAwLTgtMy41OS04LThzMy41OS04IDgtOCA4IDMuNTkgOCA4LTMuNTkgOC04IDh6IiBmaWxsPSJ3aGl0ZSIvPjwvc3ZnPg==)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

A REST API that lets users build dynamic forms through natural language conversations. Describe the form you want, and the API uses Groq's LLM to generate structured questions with proper validation rules. Iterate via follow-up prompts, publish, and collect responses, all through clean REST endpoints.

**Frontend:** [github.com/bruce-pain/formbrew-fe](https://github.com/bruce-pain/formbrew-fe) · **Live Demo:** [API Docs](https://ai-form-builder-be.onrender.com/v1/docs) · [Frontend](https://formbrew.vercel.app/)

---

## Tech Stack

| Category             | Choice                                    |
| -------------------- | ----------------------------------------- |
| Framework            | [FastAPI](https://fastapi.tiangolo.com)   |
| Database             | [PostgreSQL](https://postgresql.org)      |
| Migrations           | [Alembic](https://alembic.sqlalchemy.org) |
| LLM Provider         | [Groq API](https://groq.com)              |
| Auth                 | JWT (access + refresh tokens)             |
| Package Manager      | [uv](https://github.com/astral-sh/uv)     |
| Linting / Formatting | [Ruff](https://docs.astral.sh/ruff)       |
| Testing              | [pytest](https://pytest.org)              |

---

## Features

- **JWT Authentication** — Register, login, and token refresh with access/refresh token pairs
- **Google Sign-In** — Sign in or sign up with a Google account; existing email/password accounts are linked automatically
- **Form CRUD** — Full create, read, update, delete for forms with structured question schemas
- **AI Question Generation** — Describe a form in plain English; the LLM generates questions with appropriate types and validation rules
- **Public Response Collection** — Submit responses to published forms without authentication
- **Response Dashboard** — View all responses collected for your forms

---

## Quick Start

### Prerequisites

- Python 3.12+
- [Docker](https://docs.docker.com/get-docker/)
- A [Groq API key](https://console.groq.com/keys)

### Setup with Docker

```sh
git clone https://github.com/bruce-pain/formbrew-be.git
cd formbrew-be

cp .env.sample .env
# Fill in your environment variables (see table below)

docker compose up --build
```

The API starts at `http://localhost:8000`. Swagger docs at `http://localhost:8000/v1/docs`.

### Local Setup (without Docker)

Requires a running PostgreSQL instance.

```sh
git clone https://github.com/bruce-pain/formbrew-be.git
cd formbrew-be

cp .env.sample .env
# Fill in your environment variables (see table below)

make install
make upgrade
make run
```

### Environment Variables

| Variable               | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| `ENVIRONMENT`          | Runtime environment (`dev` or `prod`)                    |
| `DATABASE_TYPE`        | Database type (`postgresql`)                             |
| `DATABASE_NAME`        | Database name                                            |
| `DATABASE_USER`        | Database username                                        |
| `DATABASE_PASSWORD`    | Database password                                        |
| `DATABASE_HOST`        | Database host                                            |
| `DATABASE_PORT`        | Database port                                            |
| `GROQ_API_KEY`         | API key for Groq LLM access                              |
| `GOOGLE_CLIENT_ID`     | Google OAuth client ID (Google sign-in); leave empty to disable |
| `SECRET_KEY`           | Secret key for JWT signing                               |
| `ALGORITHM`            | JWT signing algorithm (`HS256`)                          |
| `ACCESS_TOKEN_EXPIRY`  | Access token lifetime in hours                           |
| `REFRESH_TOKEN_EXPIRY` | Refresh token lifetime in hours                          |

---

## API Reference

The API exposes four groups of endpoints:

| Group                | Description                                                             |
| -------------------- | ----------------------------------------------------------------------- |
| **Authentication**   | Register, login, Google sign-in, token refresh, get current user        |
| **Forms**            | Create, list, update, delete forms, and retrieve published forms publicly |
| **AI Generation**    | Generate or modify form questions using natural language prompts        |
| **Responses**        | Submit responses to published forms (public) and view collected data    |

Full request/response schemas are documented in the live Swagger UI:

- **Swagger UI:** [ai-form-builder-be.onrender.com/v1/docs](https://ai-form-builder-be.onrender.com/v1/docs)
- **ReDoc:** [ai-form-builder-be.onrender.com/v1/redoc](https://ai-form-builder-be.onrender.com/v1/redoc)

---

## Development

| Command          | Description                              |
| ---------------- | ---------------------------------------- |
| `make run`       | Start development server with hot reload |
| `make install`   | Install project dependencies             |
| `make migrate`   | Generate a new migration                 |
| `make upgrade`   | Apply all pending migrations             |
| `make downgrade` | Revert the last migration                |
| `make test`      | Run the test suite                       |
| `make lint`      | Check code for linting errors            |
| `make format`    | Format the codebase                      |

Run `make help` to see all available commands.

---

## License

[MIT](LICENSE)
