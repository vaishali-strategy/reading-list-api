# Reading List API

A small REST API for tracking books to read, reading, and finished.
Built with FastAPI, SQLModel, and SQLite.

## Endpoints
| Method | Path | What it does |
|---|---|---|
| POST | /books | Add a book (409 if title + author already exist) |
| GET | /books | List books, optional `?status=reading` filter |
| GET | /books/{id} | Get one book (404 if missing) |
| PATCH | /books/{id} | Update only the fields you send |
| DELETE | /books/{id} | Delete a book |

## Run it
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    fastapi dev main.py

Interactive docs: http://127.0.0.1:8000/docs

## Test it
    python -m pytest -v

Tests use a throwaway in-memory database via FastAPI dependency overrides.

## Design notes
- `BookCreate` is the input shape; `Book` is the table. The server owns `id`.
- Status is limited to to-read, reading, finished.
- No authentication yet. Anyone who can reach the API can edit data.
