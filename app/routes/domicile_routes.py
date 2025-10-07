import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, logger
from app import config
from app.database import open_con
from app.nitb import nitb_session, get_session

router = APIRouter()

@router.get("/check/{cnic}")
def check_domicile_status(cnic: str):
    if not cnic:
        return {"error": "CNIC is required"}

    # Remove non-digits (handles both '61101-4561237-8' and '6110145612378')
    clean_cnic = re.sub(r"\D", "", cnic)
    if len(clean_cnic) != 13:
        return {"error": "CNIC must be 13 digits (e.g., 61101-4561237-8)"}

    
    try:
        con, cur = open_con()
        if type(con) is str:
            return {"error": f"Database connection failed: {cur}"}

        cur.execute(
            "SELECT receipt_no, Status, First_Name, remarks FROM domicile WHERE cnic = %s",
            (clean_cnic,)
        )
        result = cur.fetchone()
        cur.close()
        con.close()

        if result:
            return {"status": result}
        else:
            return {"error": "Record not found"}

    except Exception as exc:
        return {"error": f"Something went wrong: {str(exc)}"}

@router.get('/statistics/check')
def statistics():
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
        if not nitb_session:
            raise HTTPException(status_code=500, detail="Unable to connect to NITB")

    url = f"{config.NITB_BASE}/dashboard/statistics"
    try:
        page = nitb_session.get(url, timeout=30)
        print(page.content)
        page.raise_for_status()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch IDP data")

    soup = BeautifulSoup(page.content, 'html.parser')
    details = {}

    for divs in soup.find_all('div', class_='bd-highlight'):
        data = divs.text.split()
        if not data:
            continue
        if data[0].strip() == 'Domicile' and len(data) >= 4:
            details['domicile'] = int(data[3]) if data[3].isdigit() else data[3]
        elif data[0].strip() == 'IDP' and len(data) >= 4:
            details['idp'] = int(data[3]) if data[3].isdigit() else data[3]

    if details:
        return details  # 👈 return dict directly instead of {'result': details}

    raise HTTPException(status_code=404, detail="No record found or IDP not approved")