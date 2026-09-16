import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, get_book_service


# =========================================================
# HELPER
# =========================================================

async def create_user_and_login(client, prefix):
    unique_id = uuid.uuid4().hex[:8]

    email = f"{prefix}_{unique_id}@test.com"
    password = "Test@12345"

    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201

    response = await client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "email": email,
        "password": password,
        "headers": {
            "Authorization": f"Bearer {token}"
        },
    }


# =========================================================
# TEST 1 - MAIN WORKFLOW
# =========================================================

@pytest.mark.asyncio
async def test_main_book_workflow():

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:

        user = await create_user_and_login(
            client,
            "workflow",
        )

        response = await client.post(
            "/books",
            json={
                "title": "Day 12 Test Book",
                "author": "Test Author",
                "isbn": f"DAY12-{uuid.uuid4().hex[:8]}",
            },
            headers=user["headers"],
        )

        assert response.status_code == 200

        book = response.json()

        assert book["title"] == "Day 12 Test Book"
        assert book["author"] == "Test Author"
        assert "id" in book

        book_id = book["id"]

        response = await client.get(
            f"/books/{book_id}",
            headers=user["headers"],
        )

        assert response.status_code == 200

        fetched_book = response.json()

        assert fetched_book["id"] == book_id
        assert fetched_book["title"] == "Day 12 Test Book"


# =========================================================
# TEST 2 - VALIDATION FAILURE
# =========================================================

@pytest.mark.asyncio
async def test_invalid_book_id_validation():

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:

        user = await create_user_and_login(
            client,
            "validation",
        )

        response = await client.get(
            "/books/0",
            headers=user["headers"],
        )

        assert response.status_code == 400

        assert response.json()["detail"] == (
            "Book ID must be greater than 0"
        )


# =========================================================
# TEST 3 - AUTHENTICATION FAILURE
# =========================================================

@pytest.mark.asyncio
async def test_invalid_login():

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:

        unique_id = uuid.uuid4().hex[:8]

        email = f"invalid_login_{unique_id}@test.com"

        response = await client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "Correct@123",
            },
        )

        assert response.status_code == 201

        response = await client.post(
            "/auth/login",
            data={
                "username": email,
                "password": "WrongPassword@123",
            },
        )

        assert response.status_code == 401

        assert response.json()["detail"] == (
            "Invalid email or password"
        )


# =========================================================
# TEST 4 - AUTHORIZATION BOUNDARY
# =========================================================

@pytest.mark.asyncio
async def test_user_cannot_access_another_users_book_day12():

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:

        user_a = await create_user_and_login(
            client,
            "owner",
        )

        user_b = await create_user_and_login(
            client,
            "other",
        )

        response = await client.post(
            "/books",
            json={
                "title": "Private Book",
                "author": "Private Author",
                "isbn": f"PRIVATE-{uuid.uuid4().hex[:8]}",
            },
            headers=user_a["headers"],
        )

        assert response.status_code == 200

        book_id = response.json()["id"]

        response = await client.get(
            f"/books/{book_id}",
            headers=user_b["headers"],
        )

        assert response.status_code == 403

        assert response.json()["detail"] == (
            "You are not authorized to access this book"
        )


# =========================================================
# TEST 5 - EXTERNAL SERVICE FAILURE
# =========================================================

@pytest.mark.asyncio
async def test_external_service_failure():

    class FailingBookService:

        async def search_books(
            self,
            query: str,
            limit: int = 10,
        ):
            from services.book_service import BookServiceError

            raise BookServiceError(
                "External book service timed out"
            )

    app.dependency_overrides[get_book_service] = (
        lambda: FailingBookService()
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:

            response = await client.get(
                "/external-books",
                params={
                    "query": "python",
                },
            )

            assert response.status_code == 503

            assert response.json()["detail"] == (
                "External book service timed out"
            )

    finally:
        app.dependency_overrides.pop(
            get_book_service,
            None,
        )