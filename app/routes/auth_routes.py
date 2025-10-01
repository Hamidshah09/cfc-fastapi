from fastapi import APIRouter, HTTPException, Depends
from app.database import open_con
from app import config
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.utils import create_access_token

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserCreate(BaseModel):
    user_name: str
    user_login: str
    password: str

class UserLogin(BaseModel):
    user_login: str
    password: str

@router.post("/register")
def register(user: UserCreate):
    con, cur = open_con()

    # check if login already exists
    cur.execute("SELECT user_id FROM users WHERE user_login = %s", (user.user_login,))
    if cur.fetchone():
        cur.close()
        con.close()
        raise HTTPException(status_code=400, detail="Login already taken")

    # hash password (bcrypt)
    hashed_password = pwd_context.hash(user.password)

    # insert new user
    cur.execute(
        """
        INSERT INTO users (user_type, main_user_id, user_name, user_login, user_pass, role, user_status, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            "Temp",        # user_type (you can change as needed)
            None,           # main_user_id (default NULL)
            user.user_name, # full name
            user.user_login,# login username
            hashed_password,# password (hashed)
            "operator",     # role default
            "active",       # status default
            None            # created_by (system, NULL for now)
        )
    )
    con.commit()

    cur.close()
    con.close()

    return {
        "message": "User registered successfully",
        "user_login": user.user_login,
        "role": "operator",
        "status": "active"
    }

@router.post("/login")
def login(user: UserLogin):
    con, cur = open_con()

    # find user
    cur.execute("SELECT * FROM users WHERE user_login = %s", (user.user_login,))
    db_user = cur.fetchone()
    cur.close()
    con.close()

    if not db_user or not pwd_context.verify(user.password, db_user["user_pass"]):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    # create JWT token
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["user_login"], "role": db_user["role"]},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
