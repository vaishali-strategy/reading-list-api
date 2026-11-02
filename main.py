import os
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI()

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Status = Literal["to-read", "reading", "finished"]

#describes database table
class Book(SQLModel, table=True):
	id: int | None = Field(default=None, primary_key=True)
	title: str
	author:str
	status: str = "to-read"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///books.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SQLModel.metadata.create_all(engine)
def get_session():
    with Session(engine) as session:
        yield session
SessionDep = Annotated[Session, Depends(get_session)]

class BookCreate(BaseModel):
    title: NonEmpty
    author: NonEmpty
    status: Status = "to-read"

class BookUpdate(BaseModel):
    title: NonEmpty | None = None
    author: NonEmpty | None = None
    status: Status | None = None

@app.get("/")
def home():
	return {"message": "Reading List API is running now"}

@app.post("/books")
def add_book(data: BookCreate, session: SessionDep):
    duplicate = session.exec(
        select(Book).where(
            func.lower(Book.title) == data.title.lower(),
            func.lower(Book.author) == data.author.lower(),
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Book already exists")
    book = Book(**data.model_dump())
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@app.get("/books")
def list_books(session: SessionDep, status: Status | None = None):
    query=select(Book)
    if status is not None:
        query=query.where(Book.status==status)
    return session.exec(query).all()

@app.get("/books/{book_id}")
def get_book(book_id: int, session: SessionDep):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.patch("/books/{book_id}")
def update_book(book_id: int, update: BookUpdate, session: SessionDep):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book

@app.delete("/books/{book_id}")
def delete_book(book_id: int, session: SessionDep):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    session.delete(book)
    session.commit()
    return {"message": "Book deleted"}


