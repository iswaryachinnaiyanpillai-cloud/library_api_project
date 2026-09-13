import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_book():

    # -----------------------------------------------------
    # Create unique test data for every test run
    # -----------------------------------------------------

    unique_id = uuid.uuid4().hex[:8]

    user_a_email = f"testusera_{unique_id}@test.com"
    user_b_email = f"testuserb_{unique_id}@test.com"

    password_a = "TestUserA@123"
    password_b = "TestUserB@123"

    test_isbn = f"TEST-AUTH-{unique_id}"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:

        # =================================================
        # REGISTER USER A
        # =================================================

        response = await client.post(
            "/auth/register",
            json={
                "email": user_a_email,
                "password": password_a,
            },
        )

        assert response.status_code == 201

        # =================================================
        # LOGIN USER A
        # =================================================

        response = await client.post(
            "/auth/login",
            data={
                "username": user_a_email,
                "password": password_a,
            },
        )

        assert response.status_code == 200

        token_a = response.json()["access_token"]

        headers_a = {
            "Authorization": f"Bearer {token_a}"
        }

        # =================================================
        # USER A CREATES A BOOK
        # =================================================

        response = await client.post(
            "/books",
            json={
                "title": "Authorization Test Book",
                "author": "Test Author",
                "isbn": test_isbn,
            },
            headers=headers_a,
        )

        assert response.status_code == 200

        book_id = response.json()["id"]

        # =================================================
        # REGISTER USER B
        # =================================================

        response = await client.post(
            "/auth/register",
            json={
                "email": user_b_email,
                "password": password_b,
            },
        )

        assert response.status_code == 201

        # =================================================
        # LOGIN USER B
        # =================================================

        response = await client.post(
            "/auth/login",
            data={
                "username": user_b_email,
                "password": password_b,
            },
        )

        assert response.status_code == 200

        token_b = response.json()["access_token"]

        headers_b = {
            "Authorization": f"Bearer {token_b}"
        }

        # =================================================
        # USER B TRIES TO ACCESS USER A'S BOOK
        # =================================================

        response = await client.get(
            f"/books/{book_id}",
            headers=headers_b,
        )

        # User B must NOT be allowed to access
        # User A's book.
        assert response.status_code == 403

        assert response.json()["detail"] == (
            "You are not authorized to access this book"
        )