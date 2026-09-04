from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    isbn: str = Field(..., min_length=1)


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