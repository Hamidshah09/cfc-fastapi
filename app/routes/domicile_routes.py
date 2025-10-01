import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, logger
from app import config
from app.database import open_con
from app.nitb import get_session

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
            return {"count": len(result), "result": result}
        else:
            raise HTTPException(status_code=404, detail="Record not found")

    except Exception as exc:
        # logger.exception("MySQL query failed: %s", exc)
        raise HTTPException(status_code=404, detail=exc)

@router.get('/statistics/check')
def statistics():
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
        if not nitb_session:
            raise HTTPException(status_code=500, detail="Unable to connect to NITB")

    url = f"{config.NITB_BASE}/dashboard/statistics"
    try:
        page = nitb_session.get(url, timeout=10)
        page.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch IDP data")

    soup = BeautifulSoup(page.content, 'html.parser')
    details = {}
    for divs in soup.find_all('div', class_='bd-highlight'):
        data = divs.text.split()
        if not data:
            continue
        if data[0].strip() == 'Domicile' and len(data) >= 4:
            details['domicile'] = data[3]
        elif data[0].strip() == 'IDP' and len(data) >= 4:
            details['idp'] = data[3]

    if details:
        return {'result':details}
    raise HTTPException(status_code=404, detail="No record found or IDP not approved")