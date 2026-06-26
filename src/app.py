"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Optional

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(current_dir, "static")),
    name="static",
)

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "very-secret-development-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_token(message: bytes) -> bytes:
    return hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()


def create_jwt(payload: dict, expires_delta: timedelta) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    now = datetime.utcnow()
    token_payload = payload.copy()
    token_payload["iat"] = int(now.timestamp())
    token_payload["exp"] = int((now + expires_delta).timestamp())

    encoded_header = base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = base64url_encode(
        json.dumps(token_payload, separators=(",", ":")).encode("utf-8")
    )
    signature = base64url_encode(
        sign_token(f"{encoded_header}.{encoded_payload}".encode("utf-8"))
    )

    return f"{encoded_header}.{encoded_payload}.{signature}"


def decode_jwt(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")

    expected_signature = base64url_encode(
        sign_token(f"{header_b64}.{payload_b64}".encode("utf-8"))
    )
    if not hmac.compare_digest(signature_b64, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    payload_data = json.loads(base64url_decode(payload_b64).decode("utf-8"))
    if payload_data.get("exp") is None or int(payload_data["exp"]) < int(datetime.utcnow().timestamp()):
        raise HTTPException(status_code=401, detail="Token has expired")

    return payload_data


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


class LoginRequest(BaseModel):
    email: str
    password: str


users = {
    "teacher@mergington.edu": {
        "password": hash_password("teacherpass"),
        "role": "teacher",
        "school": "Mergington High School",
    },
    "student@mergington.edu": {
        "password": hash_password("studentpass"),
        "role": "student",
        "school": "Mergington High School",
    },
}


def get_user(email: str) -> Optional[dict]:
    return users.get(email)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = get_user(email)
    if not user or not verify_password(password, user["password"]):
        return None
    return {"email": email, "role": user["role"], "school": user["school"]}


def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header.split(" ", 1)[1]
    payload = decode_jwt(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")

    email = payload.get("sub")
    user = get_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"email": email, "role": user["role"], "school": user["school"]}


def get_current_user_optional(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    payload = decode_jwt(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")

    email = payload.get("sub")
    user = get_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"email": email, "role": user["role"], "school": user["school"]}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(current_user: Optional[dict] = Depends(get_current_user_optional)):
    return activities


@app.post("/login")
def login(login_request: LoginRequest):
    user = authenticate_user(login_request.email, login_request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_jwt(
        {
            "sub": user["email"],
            "role": user["role"],
            "school": user["school"],
            "type": "access",
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": user["role"],
        "school": user["school"],
        "email": user["email"],
    }


@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """Sign up a student for an activity"""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]

    if current_user["role"] == "student" and current_user["email"] != email:
        raise HTTPException(
            status_code=403,
            detail="Students may only sign up themselves",
        )

    if email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """Unregister a student from an activity"""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]

    if current_user["role"] == "student" and current_user["email"] != email:
        raise HTTPException(
            status_code=403,
            detail="Students may only unregister themselves",
        )

    if email not in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
