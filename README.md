# Library Book Lending API

A RESTful API built with FastAPI and Pydantic for managing books, members, and book lending.

## Project Overview

This project is part of the ZyoraByte Python Backend Internship.

Day 1 focused on creating the FastAPI application and health-check endpoint.

Day 2 focuses on API design, Pydantic request/response models, REST endpoints, relationships, and error handling.

---

## Entities

### 1. Book

Represents a book available in the library.

Fields:

- `id` - Unique identifier for the book
- `title` - Title of the book
- `author` - Author of the book
- `isbn` - ISBN number of the book

### 2. Member

Represents a library member.

Fields:

- `id` - Unique identifier for the member
- `name` - Member's name
- `email` - Member's email address

### 3. Lending

Represents a book borrowed by a member.

Fields:

- `id` - Unique identifier for the lending record
- `book_id` - ID of the borrowed book
- `member_id` - ID of the member who borrowed the book
- `returned` - Indicates whether the book has been returned

---

## Entity Relationship

A member can borrow a book.

```text
Member (1)
    |
    | borrows
    |
    v
Lending
    |
    | refers to
    |
    v
Book (1)