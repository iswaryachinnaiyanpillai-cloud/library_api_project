# Library Book Lending API

A RESTful Library Book Lending API built with **FastAPI**, **Pydantic**, **SQLAlchemy**, and **PostgreSQL**.

The API provides authentication, book management, member management, lending workflows, authorization, search and filtering, pagination, external book-service integration, reliability handling, and automated tests.

This project was developed as part of the **ZyoraByte Python Backend Internship**.

---

## Features

- User registration and authentication
- JWT-based authentication
- Protected API endpoints
- User ownership and authorization
- Book creation and retrieval
- Book search, filtering, and pagination
- Library member management
- Book lending management
- External book search using Open Library
- Consistent error handling
- Database transaction rollback
- Structured application logging
- Automated API tests
- Isolated test database
- Database migrations using Alembic
- Interactive Swagger API documentation

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Pydantic | Request and response validation |
| SQLAlchemy | Database ORM |
| PostgreSQL | Application database |
| Alembic | Database migrations |
| JWT | Authentication |
| OAuth2 | Login authentication flow |
| HTTPX | External API requests |
| Pytest | Automated testing |
| SQLite | Isolated test database |
| Open Library API | External book data |

---

# Project Structure

```text
library_api_project/
│
├── alembic/
│   ├── versions/
│   └── ...
│
├── services/
│   ├── __init__.py
│   └── book_service.py
│
├── venv/
│
├── auth.py
├── database.py
├── db_models.py
├── main.py
├── models.py
│
├── conftest.py
├── test_authorization.py
├── test_day12.py
│
├── alembic.ini
├── requirements.txt
├── .env
├── .gitignore
└── README.md