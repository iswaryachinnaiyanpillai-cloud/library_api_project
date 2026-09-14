import logging

import httpx


logger = logging.getLogger("library_api.book_service")


class BookServiceError(Exception):
    """Raised when the external book service fails."""

    pass


class BookService:
    """
    Service layer for communicating with
    the external Open Library API.
    """

    BASE_URL = "https://openlibrary.org/search.json"

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def search_books(
        self,
        query: str,
        limit: int = 10,
    ):
        params = {
            "q": query,
            "limit": limit,
        }

        logger.info(
            "Calling external book service | "
            "query=%s | limit=%s",
            query,
            limit,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                )

                response.raise_for_status()

        except httpx.TimeoutException as exc:
            logger.error(
                "External book service timeout | "
                "query=%s",
                query,
            )

            raise BookServiceError(
                "External book service timed out"
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.error(
                "External book service HTTP error | "
                "status=%s | query=%s",
                exc.response.status_code,
                query,
            )

            raise BookServiceError(
                "External book service returned an error"
            ) from exc

        except httpx.RequestError as exc:
            logger.error(
                "External book service connection error | "
                "query=%s | error=%s",
                query,
                str(exc),
            )

            raise BookServiceError(
                "Unable to connect to external book service"
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            logger.error(
                "External book service returned invalid JSON | "
                "query=%s",
                query,
            )

            raise BookServiceError(
                "External book service returned invalid data"
            ) from exc

        books = []

        for item in data.get("docs", []):
            authors = item.get(
                "author_name",
                [],
            )

            isbn_list = item.get(
                "isbn",
                [],
            )

            books.append(
                {
                    "title": item.get(
                        "title",
                        "Unknown title",
                    ),
                    "author": (
                        authors[0]
                        if authors
                        else None
                    ),
                    "first_publish_year": item.get(
                        "first_publish_year"
                    ),
                    "isbn": (
                        isbn_list[0]
                        if isbn_list
                        else None
                    ),
                }
            )

        logger.info(
            "External book service succeeded | "
            "query=%s | results=%s",
            query,
            len(books),
        )

        return books