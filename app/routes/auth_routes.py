from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext

from app.database import open_con
from app.utils import create_access_token

router = APIRouter()

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


class TokenRequest(BaseModel):
    username: str
    password: str


@router.post("/token")
def issue_token(data: TokenRequest):
    con, cur = open_con()

    if type(con) is str:
        raise HTTPException(status_code=500, detail=cur)

    # Fetch user from DB
    cur.execute(
        "SELECT user_login, user_pass, role, user_status FROM users WHERE user_login = %s and user_pass = %s",
        (data.username, data.password)
    )
    user = cur.fetchone()

    cur.close()
    con.close()

    # Validate user
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user["user_status"] != "Active":
        raise HTTPException(status_code=403, detail="User account is inactive")


    # Create JWT
    token = create_access_token({
        "sub": user["user_login"],
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
