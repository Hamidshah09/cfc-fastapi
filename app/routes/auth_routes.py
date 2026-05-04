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
        "SELECT user_id, user_name, user_login, user_pass, role, user_status FROM users WHERE user_login = %s and user_pass = %s",
        (data.username, data.password)
    )
    user = cur.fetchone()

    

    # Validate user
    if not user:
        cur.close()
        con.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user["user_status"] != "Active":
        cur.close()
        con.close()
        raise HTTPException(status_code=403, detail="User account is inactive")
    cur.execute("Select a.status, m.module_name from allowed_modules as a Join modules as m on a.module_id = m.module_id where user_id = %s;", (user['user_id'],))
    user_modules = cur.fetchall()
    Query = """
            Select settings.setting_name, user_settings.setting_value 
            from user_settings 
            join settings 
                on user_settings.setting_id = settings.id 
            where user_settings.user_id = %s;
            """
    cur.execute(Query, (user['user_id'],))
    setting_data = cur.fetchall()
    user_settings = {}
    for row in setting_data:
        user_settings[row['setting_name']] = row['setting_value']
    cur.close()
    con.close()
    # Create JWT
    token = create_access_token({
        "sub": user["user_login"],
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
        "allowed_modules":user_modules,
        "user_settings":user_settings
    }
