"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


TEACHERS_FILE = current_dir / "teachers.json"
PASSWORD_HASH_ITERATIONS = 310_000
SESSION_MAX_AGE = 8 * 60 * 60
SESSION_COOKIE_NAME = "teacher_session"
SESSION_SECRET = os.getenv("SESSION_SECRET")
if SESSION_SECRET and len(SESSION_SECRET.encode("utf-8")) < 32:
    raise ValueError("SESSION_SECRET must be at least 32 bytes")
SESSION_SECRET_BYTES = (
    SESSION_SECRET.encode("utf-8") if SESSION_SECRET else secrets.token_bytes(32)
)
COOKIE_SECURE_SETTING = os.getenv("COOKIE_SECURE", "false").lower()
if COOKIE_SECURE_SETTING not in {"true", "false"}:
    raise ValueError("COOKIE_SECURE must be either true or false")
COOKIE_SECURE = COOKIE_SECURE_SETTING == "true"


def load_teachers() -> dict[str, dict[str, str]]:
    records = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{TEACHERS_FILE} must contain a JSON array")

    loaded_teachers: dict[str, dict[str, str]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each teacher record must be a JSON object")
        username = record.get("username")
        salt = record.get("salt")
        password_hash = record.get("password_hash")
        if (
            not isinstance(username, str)
            or not username
            or not isinstance(salt, str)
            or re.fullmatch(r"[0-9a-f]{32}", salt) is None
            or not isinstance(password_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", password_hash) is None
        ):
            raise ValueError(
                "Teacher records require a username, 32-character hex salt, "
                "and 64-character hex password_hash"
            )
        if username in loaded_teachers:
            raise ValueError(f"Duplicate teacher username: {username}")
        loaded_teachers[username] = {"salt": salt, "password_hash": password_hash}
    return loaded_teachers


teachers = load_teachers()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


def make_session_token(username: str) -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE
    payload = base64.urlsafe_b64encode(
        f"{username}:{expires_at}".encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(
        SESSION_SECRET_BYTES, payload.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"


def get_teacher_session(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Teacher login required")

    try:
        payload, signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            SESSION_SECRET_BYTES, payload.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid session signature")
        padding = "=" * (-len(payload) % 4)
        username, expires_at = base64.urlsafe_b64decode(
            payload + padding
        ).decode("utf-8").rsplit(":", 1)
        if int(expires_at) < int(time.time()) or username not in teachers:
            raise ValueError("Expired or unknown teacher session")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Teacher login required") from None
    return username


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    teacher = teachers.get(credentials.username)
    if teacher is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        credentials.password.encode("utf-8"),
        bytes.fromhex(teacher["salt"]),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    if not hmac.compare_digest(password_hash, teacher["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=make_session_token(credentials.username),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"username": credentials.username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


@app.get("/auth/me")
def current_teacher(username: str = Depends(get_teacher_session)):
    return {"username": username}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _teacher: str = Depends(get_teacher_session)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _teacher: str = Depends(get_teacher_session)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
