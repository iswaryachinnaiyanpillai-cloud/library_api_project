import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_book():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:

        # Register User A
        response = await client.post(
            "/auth/register",
            json={
                "email": "testusera@test.com",
                "password": "TestUserA@123",
            },
        )

        # Ignore if user already exists
        assert response.status_code in [201, 400]

        # Login User A
        response = await client.post(
            "/auth/login",
            data={
                "username": "testusera@test.com",
                "password": "TestUserA@123",
            },
        )

        assert response.status_code == 200

        token_a = response.json()["access_token"]

        headers_a = {
            "Authorization": f"Bearer {token_a}"
        }

        # Create a book as User A
        response = await client.post(
            "/books",
            json={
                "title": "Authorization Test Book",
                "author": "Test Author",
                "isbn": "TEST-AUTH-001",
            },
            headers=headers_a,
        )

        assert response.status_code == 200

        book_id = response.json()["id"]

        # Register User B
        response = await client.post(
            "/auth/register",
            json={
                "email": "testuserb@test.com",
                "password": "TestUserB@123",
            },
        )

        assert response.status_code in [201, 400]

        # Login User B
        response = await client.post(
            "/auth/login",
            data={
                "username": "testuserb@test.com",
                "password": "TestUserB@123",
            },
        )

        assert response.status_code == 200

        token_b = response.json()["access_token"]

        headers_b = {
            "Authorization": f"Bearer {token_b}"
        }

        # User B attempts to access User A's book
        response = await client.get(
            f"/books/{book_id}",
            headers=headers_b,
        )

        # Authorization must block access
        assert response.status_code == 403
        assert response.json()["detail"] == (
            "You are not authorized to access this book"
        )