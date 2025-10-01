import re
from fastapi import APIRouter, HTTPException, logger
from app.database import open_con

router = APIRouter()

@router.get("/check/{cnic}")
def check_domicile_status(cnic:str):
    if not cnic:
        raise HTTPException(status_code=404, detail="Record not found")

    clean_cnic = re.sub(r"\D", '', cnic)
    if len(clean_cnic) != 13:
        raise HTTPException(status_code=401, detail="cnic is not 13 digits")

    try:
        con, cur = open_con()
        if type(con) is str:
            raise HTTPException(status_code=500, detail=cur)
        cur.execute(
            "SELECT receipt_no, Status, First_Name, remarks FROM domicile WHERE cnic = %s",
            (clean_cnic,)
        )
        result = cur.fetchone()
        cur.close()
        con.close()

        if result:
            {"count": len(result), "result": result}
        else:
            raise HTTPException(status_code=404, detail="Record not found")

    except Exception as exc:
        logger.exception("MySQL query failed: %s", exc)
        raise HTTPException(status_code=404, detail=exc)