from pydantic import BaseModel
from typing import Optional


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str


class MemberCreate(BaseModel):
    name: str
    email: str


class MemberResponse(BaseModel):
    id: int
    name: str
    email: str


class LendingCreate(BaseModel):
    book_id: int
    member_id: int


class LendingResponse(BaseModel):
    id: int
    book_id: int
    member_id: int
    returned: bool