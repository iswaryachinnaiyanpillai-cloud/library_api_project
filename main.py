from fastapi import FastAPI, HTTPException
from models import (
    BookCreate,
    BookResponse,
    MemberCreate,
    MemberResponse,
    LendingCreate,
    LendingResponse
)

app = FastAPI(title="Library Book Lending API")


# Health check - Day 1
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# -------------------------
# Book endpoints
# -------------------------

@app.post("/books", response_model=BookResponse)
def create_book(book: BookCreate):
    return {
        "id": 1,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn
    }


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int):

    if book_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Book ID must be greater than 0"
        )

    return {
        "id": book_id,
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "isbn": "9780061122415"
    }


# -------------------------
# Member endpoints
# -------------------------

@app.post("/members", response_model=MemberResponse)
def create_member(member: MemberCreate):
    return {
        "id": 1,
        "name": member.name,
        "email": member.email
    }


@app.get("/members/{member_id}", response_model=MemberResponse)
def get_member(member_id: int):

    if member_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Member ID must be greater than 0"
        )

    return {
        "id": member_id,
        "name": "Sample Member",
        "email": "member@example.com"
    }


# -------------------------
# Lending endpoints
# -------------------------

@app.post("/lendings", response_model=LendingResponse)
def create_lending(lending: LendingCreate):

    if lending.book_id <= 0 or lending.member_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Book ID and Member ID must be greater than 0"
        )

    return {
        "id": 1,
        "book_id": lending.book_id,
        "member_id": lending.member_id,
        "returned": False
    }


@app.get("/lendings/{lending_id}", response_model=LendingResponse)
def get_lending(lending_id: int):

    if lending_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Lending ID must be greater than 0"
        )

    return {
        "id": lending_id,
        "book_id": 1,
        "member_id": 1,
        "returned": False
    }