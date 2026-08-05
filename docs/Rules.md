# Development Rules

These rules must be followed for every implementation in this project.

---

# 1. Analyze and Verify Before Implementing

Before writing any code, always follow this checklist:

- Understand the existing project structure.
- Search the project for similar/existing functionality or utilities.
- Follow the existing architecture and coding style.
- Reuse existing models, services, and utilities whenever possible.
- Follow naming conventions.
- Keep implementation modular.
- Do not introduce a new pattern if an existing one already solves the problem.
- Never assume something doesn't already exist — only after verifying, write new code.

---

# 2. Never Duplicate Code — Always Reuse Existing Utilities

Before writing new logic, search whether similar logic already exists. Reuse existing functions/utilities instead of copy-pasting or recreating them in every module.

### ✅ Good

```python
PasswordHasher.hash()
```

Used everywhere, and reused from `shared/utils/date.py` for date logic, etc.

### ❌ Bad

Copying password hashing logic into multiple services, or creating `date_utils.py` inside every module.

---

# 3. No Hardcoded Messages

Never write user-facing messages directly.

All messages must come from shared constants.

### ✅ Good

```python
Messages.USER_CREATED
Messages.PRODUCT_NOT_FOUND
```

### ❌ Bad

```python
return {
    "message": "User created successfully"
}
```

---

# 4. Use Common API Response Models

All APIs must follow the same response structure.

### Detail Response

```json
{
  "success": true,
  "status": 200,
  "message": "User fetched successfully",
  "data": {}
}
```

### List Response

```json
{
  "success": true,
  "status": 200,
  "message": "Users fetched successfully",
  "data": [],
 "pagination": {
    "currentPage": 1,
    "totalPages": 10,
    "totalItems": 120,
    "itemsPerPage": 10,
    "hasNextPage": true,
    "hasPrevPage": false,
},
}
```

### ❌ Bad

Different response formats for different APIs.

---

# 5. Keep Functions Small and Short

One function should have one responsibility, and should generally stay under **30-40 lines**. If a function grows too large, split it into helper functions.

### ✅ Good

```python
validate_password()

create_user()

send_email()
```

### ❌ Bad

One 300-line function doing validation, database operations, email sending and logging.

---

# 6. Avoid Deep Nesting

Prefer early returns.

### ❌ Bad

```python
if:
    if:
        if:
            if:
```

### ✅ Good

```python
if not user:
    return

process_user()
```

---

# 7. Keep Constants Centralized — Avoid Magic Numbers and Strings

Never hardcode values that may change. Define them as named constants in a centralized location.

### ✅ Good

```python
DEFAULT_PAGE_SIZE = 20

MAX_LOGIN_ATTEMPTS = 5
```

### ❌ Bad

```python
page_size = 20

if attempts > 5:
```

---

# 8. Follow Naming Conventions

Classes

```python
PascalCase
```

Functions

```python
snake_case
```

Constants

```python
UPPER_CASE
```

Files

```python
snake_case.py
```

---

# 9. Keep Imports Organized and at the Top of the File

All import statements must be placed at the beginning of the file, ordered as:

```python
# Standard Library

# Third-party Packages

# Project Imports
```

Never import modules inside functions, loops, or conditional blocks unless there is a very specific and documented reason (such as avoiding circular imports or optional dependencies).

### ✅ Good

```python
import uuid

from fastapi import APIRouter

from app.shared.responses import Response
from app.modules.users.service import UserService


def create_user():
    ...
```

### ❌ Bad

```python
def create_user():
    from app.modules.users.service import UserService

    service = UserService()
```

---

# 10. Write Reusable Code

If logic can be reused later, make it generic instead of module-specific.

### ✅ Good

```python
Pagination

BaseResponse

FileUploader
```

### ❌ Bad

```python
ProductPagination

OrderPagination

UserPagination
```

---

# 11. Follow Existing Coding Style

When modifying existing code:

- Follow existing formatting.
- Follow existing naming.
- Follow existing architecture.
- Minimize unnecessary changes.

---

# 12. Do Not Break Existing Functionality

Before modifying existing code:

- Understand current implementation.
- Preserve backward compatibility.
- Modify only the required files.

---

# 13. Production-Ready Code Only

Every implementation should be:

- Clean
- Readable
- Reusable
- Typed
- Well documented
- Scalable
- Maintainable

Avoid temporary fixes or hacky implementations.

---

# 14. Explain Changes

Whenever implementing a feature:

- Explain what was changed.
- List created files.
- List modified files.
- Explain why the approach was chosen.

---

# 15. Avoid Wildcard Imports

Never use wildcard imports.

### ✅ Good

```python
from app.shared.messages import Messages
```

### ❌ Bad

```python
from app.shared.messages import *
```

---

# 16. Remove Unused Imports

Only import what is actually used.

### ✅ Good

```python
from fastapi import APIRouter
```

### ❌ Bad

```python
from fastapi import APIRouter, Depends, UploadFile, HTTPException, Request
```

when only `APIRouter` is used.

---

# 17. Write Self-Explanatory Code

Code should explain itself.

Avoid unnecessary comments for obvious code.

### ✅ Good

```python
is_email_verified = True
```

### ❌ Bad

```python
x = True
```

---

# 18. Never Access Environment Variables Directly

Read environment variables only through the configuration module.

### ✅ Good

```python
settings.DATABASE_URL
```

### ❌ Bad

```python
os.getenv("DATABASE_URL")
```

inside random files.

---

# 19. Don't Catch Generic Exceptions

Catch only specific exceptions whenever possible.

### ✅ Good

```python
except ValueError:
```

### ❌ Bad

```python
except Exception:
```

---

# 20. Always Log Exceptions

Unexpected errors should be logged before being returned.

### ✅ Good

```python
logger.exception(error)
raise InternalServerException()
```

### ❌ Bad

```python
except Exception:
    pass
```

---

# 21. Never Leave Dead Code

Remove:

- commented code
- unused functions
- unused variables
- old implementations

### ❌ Bad

```python
# old_create_user()
#
# def test():
#     ...
```

---

# 22. Never Leave TODOs in Production Code

Resolve TODOs before merging.

### ❌ Bad

```python
# TODO:
# implement later
```

---

# 23. Follow Consistent API Naming

REST endpoints should use nouns, not verbs.

### ✅ Good

```
GET /users

POST /users

GET /users/{id}
```

### ❌ Bad

```
POST /create-user

GET /getUsers

POST /deleteUser
```

---

# 24. Limit Cognitive Complexity

Functions should have a cognitive complexity of 15 or less.

If a function has too many nested loops, if statements, or complex branching logic, break it down into smaller, focused helper functions.

### ✅ Good

Extracting loops and conditions into separate helper functions to keep the main function flat and readable.

### ❌ Bad

Having multiple nested `if`, `for`, and conditional expressions in a single function (Cognitive Complexity > 15).

---

# 25. Helper Functions Must Reside in Helper Files

All utility and helper logic must be placed in a dedicated file (e.g., `helpers.py`) instead of bloating the router files. Routers should only be responsible for endpoint routing and orchestrating high-level calls.

### ✅ Good

Extracting helper logic to `helpers.py` and importing them into `routers/admin.py`.

### ❌ Bad

Defining multiple helper functions, data transformers, or queries directly inside a router file.

---

# Final Rule

**Think → Analyze → Reuse → Implement**

Never start coding immediately.

Always analyze the existing project first, then implement the most maintainable and reusable solution.