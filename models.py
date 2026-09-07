from pydantic import BaseModel, Field, EmailStr


# -------------------------
# Book schemas
# -------------------------

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    isbn: str = Field(..., min_length=1)


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str


# -------------------------
# Member schemas
# -------------------------

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr


class MemberResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


# -------------------------
# Lending schemas
# -------------------------

class LendingCreate(BaseModel):
    book_id: int
    member_id: int


class LendingResponse(BaseModel):
    id: int
    book_id: int
    member_id: int
    returned: bool


# -------------------------
# Authentication schemas
# -------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str