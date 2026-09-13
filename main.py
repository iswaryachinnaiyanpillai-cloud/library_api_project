from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    verify_access_token,
    verify_password,
)

from database import AsyncSessionLocal
from db_models import Book, Lending, Member, User

from models import (
    BookCreate,
    BookResponse,
    LendingCreate,
    LendingResponse,
    MemberCreate,
    MemberResponse,
    Token,
    UserCreate,
    UserResponse,
)

from services.book_service import (
    BookService,
    BookServiceError,
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Library Book Lending API",
    version="1.0.0",
)


# =========================================================
# DAY 10 - SERVICE DEPENDENCY
# =========================================================

def get_book_service():
    return BookService()


# =========================================================
# DAY 10 - EXTERNAL BOOK RESPONSE
# =========================================================

class ExternalBookResponse(BaseModel):
    title: str
    author: str | None = None
    first_publish_year: int | None = None
    isbn: str | None = None


# =========================================================
# DATABASE DEPENDENCY
# =========================================================

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# =========================================================
# AUTHENTICATION DEPENDENCY
# =========================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_access_token(token)

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return user


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# =========================================================
# AUTHENTICATION ENDPOINTS
# =========================================================


# ---------------------------------------------------------
# Register
# ---------------------------------------------------------

@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == user.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = hash_password(user.password)

    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
    )

    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)

    except IntegrityError:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    except Exception as exc:
        await db.rollback()

        print("USER REGISTER ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to register user",
        )

    return {
        "id": new_user.id,
        "email": new_user.email,
    }


# ---------------------------------------------------------
# Login
# ---------------------------------------------------------

@app.post(
    "/auth/login",
    response_model=Token,
)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.email == form_data.username
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ---------------------------------------------------------
# Current logged-in user
# ---------------------------------------------------------

@app.get(
    "/auth/me",
    response_model=UserResponse,
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
    }


# =========================================================
# DAY 9 - BOOK SEARCH, FILTERS AND PAGINATION
# =========================================================

@app.get(
    "/books",
    response_model=list[BookResponse],
)
async def list_books(
    title: str | None = Query(None),
    author: str | None = Query(None),
    isbn: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Start with only the current user's books.
    query = select(Book).where(
        Book.owner_id == current_user.id
    )

    # Title filter
    if title:
        query = query.where(
            Book.title.ilike(f"%{title}%")
        )

    # Author filter
    if author:
        query = query.where(
            Book.author.ilike(f"%{author}%")
        )

    # ISBN filter
    if isbn:
        query = query.where(
            Book.isbn.ilike(f"%{isbn}%")
        )

    # Filtering is performed in SQL first.
    # Pagination is applied after filtering.
    query = (
        query
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)

    books = result.scalars().all()

    # Empty results return [].
    return books


# =========================================================
# DAY 10 - EXTERNAL BOOK SEARCH
# =========================================================

@app.get(
    "/external-books",
    response_model=list[ExternalBookResponse],
)
async def search_external_books(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
    service: BookService = Depends(get_book_service),
):
    try:
        return await service.search_books(
            query=query,
            limit=limit,
        )

    except BookServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


# =========================================================
# BOOK CREATE
# =========================================================

@app.post(
    "/books",
    response_model=BookResponse,
)
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        new_book = Book(
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            owner_id=current_user.id,
        )

        db.add(new_book)

        await db.commit()
        await db.refresh(new_book)

        return new_book

    except HTTPException:
        await db.rollback()
        raise

    except IntegrityError as exc:
        await db.rollback()

        print("BOOK INTEGRITY ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A book with this ISBN already exists.",
        )

    except Exception as exc:
        await db.rollback()

        # Temporary diagnostic output so the actual
        # database problem is visible during testing.
        print("BOOK CREATE ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# =========================================================
# GET BOOK BY ID
# =========================================================

@app.get(
    "/books/{book_id}",
    response_model=BookResponse,
)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be greater than 0",
        )

    result = await db.execute(
        select(Book).where(
            Book.id == book_id,
            Book.owner_id == current_user.id,
        )
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this book",
        )

    return book


# =========================================================
# MEMBER ENDPOINTS
# =========================================================


# ---------------------------------------------------------
# Create member
# ---------------------------------------------------------

@app.post(
    "/members",
    response_model=MemberResponse,
)
async def create_member(
    member: MemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        new_member = Member(
            name=member.name,
            email=member.email,
            owner_id=current_user.id,
        )

        db.add(new_member)

        await db.commit()
        await db.refresh(new_member)

        return new_member

    except IntegrityError as exc:
        await db.rollback()

        print("MEMBER INTEGRITY ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create member because of a database constraint.",
        )

    except Exception as exc:
        await db.rollback()

        print("MEMBER CREATE ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create member",
        )


# ---------------------------------------------------------
# Get member
# ---------------------------------------------------------

@app.get(
    "/members/{member_id}",
    response_model=MemberResponse,
)
async def get_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if member_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member ID must be greater than 0",
        )

    result = await db.execute(
        select(Member).where(
            Member.id == member_id,
            Member.owner_id == current_user.id,
        )
    )

    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this member",
        )

    return member


# =========================================================
# LENDING ENDPOINTS
# =========================================================


# ---------------------------------------------------------
# Create lending
# ---------------------------------------------------------

@app.post(
    "/lendings",
    response_model=LendingResponse,
)
async def create_lending(
    lending: LendingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        if (
            lending.book_id <= 0
            or lending.member_id <= 0
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Book ID and Member ID "
                    "must be greater than 0"
                ),
            )

        # Check book ownership
        book_result = await db.execute(
            select(Book).where(
                Book.id == lending.book_id,
                Book.owner_id == current_user.id,
            )
        )

        book = book_result.scalar_one_or_none()

        if book is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to use this book",
            )

        # Check member ownership
        member_result = await db.execute(
            select(Member).where(
                Member.id == lending.member_id,
                Member.owner_id == current_user.id,
            )
        )

        member = member_result.scalar_one_or_none()

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to use this member",
            )

        new_lending = Lending(
            book_id=lending.book_id,
            member_id=lending.member_id,
            returned=False,
            owner_id=current_user.id,
        )

        db.add(new_lending)

        await db.commit()
        await db.refresh(new_lending)

        return new_lending

    except HTTPException:
        await db.rollback()
        raise

    except IntegrityError as exc:
        await db.rollback()

        print("LENDING INTEGRITY ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create lending because of a database constraint.",
        )

    except Exception as exc:
        await db.rollback()

        print("LENDING CREATE ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create lending",
        )


# ---------------------------------------------------------
# Get lending
# ---------------------------------------------------------

@app.get(
    "/lendings/{lending_id}",
    response_model=LendingResponse,
)
async def get_lending(
    lending_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if lending_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lending ID must be greater than 0",
        )

    result = await db.execute(
        select(Lending).where(
            Lending.id == lending_id,
            Lending.owner_id == current_user.id,
        )
    )

    lending = result.scalar_one_or_none()

    if lending is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this lending",
        )

    return lending