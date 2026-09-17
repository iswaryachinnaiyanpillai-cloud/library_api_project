import logging

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse
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

from db_models import (
    Book,
    Lending,
    Member,
    User,
)

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
# LOGGING CONFIGURATION
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("library_api")


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Library Book Lending API",
    description=(
        "A RESTful API for managing library books, members, "
        "and lending records with authentication, authorization, "
        "search, pagination, external book-service integration, "
        "reliability handling, and automated testing."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# =========================================================
# GLOBAL UNEXPECTED ERROR HANDLER
# =========================================================

@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unexpected application error",
        extra={
            "method": request.method,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error. Please try again later."
        },
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
        try:
            yield session

        except Exception:
            await session.rollback()

            logger.exception(
                "Database session rolled back after unexpected error"
            )

            raise

        finally:
            await session.close()


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
# DAY 14 - HEALTH CHECK
# =========================================================

@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    try:
        await db.execute(select(1))

        return {
            "status": "healthy",
            "database": "healthy",
        }

    except Exception as exc:
        logger.exception(
            "Health check failed: database is unavailable"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc


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

        logger.info(
            "User registered successfully",
            extra={
                "user_id": new_user.id,
                "email": new_user.email,
            },
        )

    except IntegrityError:
        await db.rollback()

        logger.warning(
            "User registration failed because email already exists"
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    except Exception as exc:
        await db.rollback()

        logger.exception(
            "Unexpected error during user registration"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register user",
        ) from exc

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
        logger.warning(
            "Login failed: invalid email"
        )

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
        logger.warning(
            "Login failed: invalid password",
            extra={
                "user_id": user.id,
            },
        )

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

    logger.info(
        "User logged in successfully",
        extra={
            "user_id": user.id,
        },
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
    query = select(Book).where(
        Book.owner_id == current_user.id
    )

    if title:
        query = query.where(
            Book.title.ilike(f"%{title}%")
        )

    if author:
        query = query.where(
            Book.author.ilike(f"%{author}%")
        )

    if isbn:
        query = query.where(
            Book.isbn.ilike(f"%{isbn}%")
        )

    query = (
        query
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )

    try:
        result = await db.execute(query)

        books = result.scalars().all()

        logger.info(
            "Books listed successfully",
            extra={
                "user_id": current_user.id,
                "skip": skip,
                "limit": limit,
                "result_count": len(books),
            },
        )

        return books

    except Exception as exc:
        logger.exception(
            "Unexpected error while listing books",
            extra={
                "user_id": current_user.id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve books",
        ) from exc


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
        books = await service.search_books(
            query=query,
            limit=limit,
        )

        return books

    except BookServiceError as exc:
        logger.warning(
            "External book service failed",
            extra={
                "query": query,
                "limit": limit,
                "reason": str(exc),
            },
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected external book service error",
            extra={
                "query": query,
                "limit": limit,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External book service is currently unavailable",
        ) from exc


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

        logger.info(
            "Book created successfully",
            extra={
                "user_id": current_user.id,
                "book_id": new_book.id,
            },
        )

        return new_book

    except IntegrityError as exc:
        await db.rollback()

        logger.warning(
            "Book creation failed because of database constraint",
            extra={
                "user_id": current_user.id,
                "isbn": book.isbn,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A book with this ISBN already exists.",
        ) from exc

    except Exception as exc:
        await db.rollback()

        logger.exception(
            "Unexpected error while creating book",
            extra={
                "user_id": current_user.id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create book",
        ) from exc


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

        logger.info(
            "Member created successfully",
            extra={
                "user_id": current_user.id,
                "member_id": new_member.id,
            },
        )

        return new_member

    except IntegrityError as exc:
        await db.rollback()

        logger.warning(
            "Member creation failed because of database constraint",
            extra={
                "user_id": current_user.id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create member because of a database constraint.",
        ) from exc

    except Exception as exc:
        await db.rollback()

        logger.exception(
            "Unexpected error while creating member",
            extra={
                "user_id": current_user.id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create member",
        ) from exc


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

        logger.info(
            "Lending created successfully",
            extra={
                "user_id": current_user.id,
                "lending_id": new_lending.id,
                "book_id": lending.book_id,
                "member_id": lending.member_id,
            },
        )

        return new_lending

    except HTTPException:
        await db.rollback()
        raise

    except IntegrityError as exc:
        await db.rollback()

        logger.warning(
            "Lending creation failed because of database constraint",
            extra={
                "user_id": current_user.id,
                "book_id": lending.book_id,
                "member_id": lending.member_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create lending because of a database constraint.",
        ) from exc

    except Exception as exc:
        await db.rollback()

        logger.exception(
            "Unexpected error while creating lending",
            extra={
                "user_id": current_user.id,
                "book_id": lending.book_id,
                "member_id": lending.member_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create lending",
        ) from exc


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