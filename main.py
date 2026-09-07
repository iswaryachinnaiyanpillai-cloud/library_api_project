from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


app = FastAPI(
    title="Library Book Lending API",
    version="1.0.0",
)


# -------------------------
# Database dependency
# -------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# -------------------------
# Authentication dependency
# -------------------------

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


# -------------------------
# Health check
# -------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# =========================================================
# AUTHENTICATION ENDPOINTS
# =========================================================

# -------------------------
# Register
# -------------------------

@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = hash_password(user.password)

    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
    )

    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)

    except Exception:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to register user",
        )

    return {
        "id": new_user.id,
        "email": new_user.email,
    }


# -------------------------
# Login
# -------------------------

@app.post(
    "/auth/login",
    response_model=Token,
)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2PasswordRequestForm uses "username".
    # We use it to carry the user's email.
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

    # Verify password
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

    # Create JWT
    access_token = create_access_token(
        data={
            "sub": str(user.id),
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# -------------------------
# Current logged-in user
# -------------------------

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
# BOOK ENDPOINTS
# =========================================================

# -------------------------
# List books
# -------------------------

@app.get(
    "/books",
    response_model=list[BookResponse],
)
async def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Book)
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )

    books = result.scalars().all()

    return books


# -------------------------
# Create book
# -------------------------

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
        )

        db.add(new_book)

        await db.commit()
        await db.refresh(new_book)

        return new_book

    except Exception:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create book",
        )


# -------------------------
# Get book by ID
# -------------------------

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
        select(Book).where(Book.id == book_id)
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    return book


# =========================================================
# MEMBER ENDPOINTS
# =========================================================

# -------------------------
# Create member
# -------------------------

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
        )

        db.add(new_member)

        await db.commit()
        await db.refresh(new_member)

        return new_member

    except Exception:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create member",
        )


# -------------------------
# Get member
# -------------------------

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
        select(Member).where(Member.id == member_id)
    )

    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return member


# =========================================================
# LENDING ENDPOINTS
# =========================================================

# -------------------------
# Create lending
# -------------------------

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

        # Check book
        book_result = await db.execute(
            select(Book).where(
                Book.id == lending.book_id
            )
        )

        book = book_result.scalar_one_or_none()

        if book is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Check member
        member_result = await db.execute(
            select(Member).where(
                Member.id == lending.member_id
            )
        )

        member = member_result.scalar_one_or_none()

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create lending",
        )


# -------------------------
# Get lending
# -------------------------

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
            Lending.id == lending_id
        )
    )

    lending = result.scalar_one_or_none()

    if lending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lending not found",
        )

    return lending