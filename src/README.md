# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher-only student registration and unregistration
- Students can view activities and their participants without logging in
- Teacher login with salted PBKDF2 password hashes

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                              | Description                                     |
| ------ | --------------------------------------------------------------------- | ----------------------------------------------- |
| GET    | `/activities`                                                         | Get all activities and participants            |
| POST   | `/auth/login`                                                         | Log in with a teacher username and password     |
| GET    | `/auth/me`                                                            | Get the current teacher login                  |
| POST   | `/auth/logout`                                                        | Log out                                         |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu`     | Register a student (teacher login required)    |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher login required)  |

## Configure teacher accounts

Teacher accounts are loaded from `src/teachers.json` when the server starts.
The file contains an array of records with `username`, a random 16-byte hex
`salt`, and a PBKDF2-SHA256 `password_hash` (64 hex characters). Plaintext
passwords are never stored. Generate a record and add it to the array with:

```python
import getpass
import hashlib
import json
import secrets

username = input("Teacher username: ")
password = getpass.getpass("Teacher password: ")
salt = secrets.token_bytes(16)
password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
print(json.dumps({
    "username": username,
    "salt": salt.hex(),
    "password_hash": password_hash.hex(),
}, indent=2))
```

Do not commit real teacher account records to a public repository. Restart the
server after updating the file. Set `SESSION_SECRET` to a persistent random
secret of at least 32 bytes and set `COOKIE_SECURE=true` when serving the app
over HTTPS. Without `SESSION_SECRET`, sessions use a temporary key and are
invalidated when the server restarts.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
