from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from db_models import Book, Member, Lending

from models import (
    BookCreate,
    BookResponse,
    MemberCreate,
    MemberResponse,
    LendingCreate,
    LendingResponse,
)


app = FastAPI(title="Library Book Lending API")


# -------------------------
# Database dependency
# -------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# -------------------------
# Health check
# -------------------------

@app.get("/health")
def health_check():
    return {"status": "healthy"}


# -------------------------
# Book endpoints
# -------------------------

# Day 5: List books with pagination
@app.get("/books", response_model=list[BookResponse])
async def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Book)
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )

    books = result.scalars().all()

    return books


# Day 4: Create book
@app.post("/books", response_model=BookResponse)
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        new_book = Book(
            title=book.title,
            author=book.author,
            isbn=book.isbn,
        )

        db.add(new_book)
        await db.commit()
        await db.refresh(new_book)

        return new_book

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Unable to create book",
        )


# Day 5: Get book by ID
@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
):
    if book_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Book ID must be greater than 0",
        )

    result = await db.execute(
        select(Book).where(Book.id == book_id)
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found",
        )

    return book


# -------------------------
# Member endpoints
# -------------------------

@app.post("/members", response_model=MemberResponse)
async def create_member(
    member: MemberCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        new_member = Member(
            name=member.name,
            email=member.email,
        )

        db.add(new_member)
        await db.commit()
        await db.refresh(new_member)

        return new_member

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Unable to create member",
        )


@app.get("/members/{member_id}", response_model=MemberResponse)
async def get_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
):
    if member_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Member ID must be greater than 0",
        )

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )

    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    return member


# -------------------------
# Lending endpoints
# -------------------------

@app.post("/lendings", response_model=LendingResponse)
async def create_lending(
    lending: LendingCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        if lending.book_id <= 0 or lending.member_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="Book ID and Member ID must be greater than 0",
            )

        book_result = await db.execute(
            select(Book).where(Book.id == lending.book_id)
        )

        book = book_result.scalar_one_or_none()

        if book is None:
            raise HTTPException(
                status_code=404,
                detail="Book not found",
            )

        member_result = await db.execute(
            select(Member).where(Member.id == lending.member_id)
        )

        member = member_result.scalar_one_or_none()

        if member is None:
            raise HTTPException(
                status_code=404,
                detail="Member not found",
            )

        new_lending = Lending(
            book_id=lending.book_id,
            member_id=lending.member_id,
            returned=False,
        )

        db.add(new_lending)
        await db.commit()
        await db.refresh(new_lending)

        return new_lending

    except HTTPException:
        await db.rollback()
        raise

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Unable to create lending",
        )


@app.get("/lendings/{lending_id}", response_model=LendingResponse)
async def get_lending(
    lending_id: int,
    db: AsyncSession = Depends(get_db),
):
    if lending_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Lending ID must be greater than 0",
        )

    result = await db.execute(
        select(Lending).where(Lending.id == lending_id)
    )

    lending = result.scalar_one_or_none()

    if lending is None:
        raise HTTPException(
            status_code=404,
            detail="Lending not found",
        )

    return lending