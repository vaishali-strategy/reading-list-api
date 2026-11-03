import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app, get_session


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()

def make_book(client, title="Atomic Habits", author="James Clear", **extra):
    return client.post("/books", json={"title": title, "author": author, **extra})
#"sqlite://" with no filename is a database that lives only in memory. 
#StaticPool keeps one connection so the tables don't disappear between calls.

def test_add_book(client):
    response = make_book(client)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Atomic Habits"
    assert data["status"] == "to-read"

def test_duplicate_returns_409(client):
    make_book(client)
    response = make_book(client)
    assert response.status_code == 409


def test_empty_author_returns_422(client):
    response = make_book(client, author="")
    assert response.status_code == 422

def test_get_missing_book_returns_404(client):
    assert client.get("/books/99").status_code == 404

def test_update_only_changes_sent_fields(client):
    make_book(client)
    response = client.patch("/books/1", json={"status": "finished"})
    assert response.status_code == 200
    assert response.json()["status"] == "finished"
    assert response.json()["title"] == "Atomic Habits"

def test_filter_by_status(client):
    make_book(client, title="A", author="X", status="reading")
    make_book(client, title="B", author="Y")
    response = client.get("/books", params={"status": "reading"})
    assert [b["title"] for b in response.json()] == ["A"]

def test_delete_book(client):
    make_book(client)
    assert client.delete("/books/1").status_code == 200
    assert client.get("/books/1").status_code == 404

def test_invalid_status_filter_returns_422(client):
    response = client.get("/books", params={"status": "banana"})
    assert response.status_code == 422

def test_patch_null_returns_422(client):
    make_book(client)
    response = client.patch("/books/1", json={"title": None})
    assert response.status_code == 422

def test_patch_into_duplicate_returns_409(client):
    make_book(client, title="Dune", author="Frank Herbert")
    make_book(client, title="Foundation", author="Isaac Asimov")

    # PATCH book 2 so it matches book 1 -> should be refused
    response = client.patch(
        "/books/2", json={"title": "Dune", "author": "Frank Herbert"}
    )
    assert response.status_code == 409

    # the refused PATCH must not have changed book 2
    assert client.get("/books/2").json()["title"] == "Foundation"

    # patching only the status is fine: a book is not a duplicate of itself
    response = client.patch("/books/2", json={"status": "reading"})
    assert response.status_code == 200
