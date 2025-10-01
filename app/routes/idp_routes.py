import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query
from app import config
from app.auth import get_current_user
from app.database import open_con
from app.nitb import nitb_session, get_session
from datetime import datetime
from typing import Optional, List
import threading

router = APIRouter()
@router.get('/check/{idp}')
def check_idp_status(idp:str):
    if not idp:
        raise HTTPException(status_code=404, detail="Record not found")

    idp = re.sub(r"\D", '', idp)
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
    
    if not nitb_session:
        raise HTTPException(status_code=500, detail="unableto connect to NITB")

    url = f"https://admin-icta.nitb.gov.pk/idp/applications?keyword={idp}&from=&to=&status="
    try:
        page = nitb_session.get(url, timeout=10)
        print(page.content)
        page.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch IDP data")

    soup = BeautifulSoup(page.content, 'html.parser')
    records = []
    for row in soup.find_all('tr'):
        tab = 0
        record_details = {}
        for td in row.find_all('td'):
            tab += 1
            text = td.text.strip()
            if tab == 2:
                record_details['Application Date'] = text
            elif tab == 3:
                record_details['Name'] = text
            elif tab == 4:
                record_details['CNIC'] = text
            elif tab == 5:
                record_details['Request Type'] = text
            elif tab == 6:
                record_details['Application Type'] = text
            elif tab == 7:
                record_details['Payment Mode'] = text
            elif tab == 8:
                record_details['Token No'] = text
            elif tab == 9:
                record_details['Status'] = text
            elif tab == 10:
                records.append(record_details)

    for record in records:
        token = record.get('Token No', '').replace('-', '')
        if token == idp:
            record['idp'] = idp
            return {'result':record}

    raise HTTPException(status_code=404, detail="No record found or IDP not approved")

def load(keyword: str = "") -> List[dict]:
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
        if not nitb_session:
            raise HTTPException(status_code=500, detail="Unable to connect to NITB")

    if keyword:
        url = f"https://admin-icta.nitb.gov.pk/idp/applications?keyword={keyword}&from=&to=&status="
    else:
        url = "https://admin-icta.nitb.gov.pk/idp/applications"

    page = nitb_session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    records = []
    for row in soup.find_all("tr"):
        record_details = {}
        for idx, td in enumerate(row.find_all("td"), start=1):
            text = td.text.strip()
            if idx == 2:
                record_details["Application Date"] = text
            elif idx == 3:
                record_details["Name"] = text
            elif idx == 4:
                record_details["CNIC"] = text
            elif idx == 5:
                record_details["Request Type"] = text
            elif idx == 6:
                record_details["Application Type"] = text
            elif idx == 7:
                record_details["Payment Mode"] = text
            elif idx == 8:
                record_details["Token No"] = text
            elif idx == 9:
                record_details["Status"] = text
        if record_details:
            records.append(record_details)

    return records


# ✅ Trigger update of all today's applications
@router.get("/update/all")
def idp_update_all():
    global nitb_session, auto_update_enabled
    if nitb_session is None:
        nitb_session = get_session()
        if not nitb_session:
            raise HTTPException(status_code=500, detail="Unable to connect to NITB")

    auto_update_enabled = True
    today = datetime.today().date()
    url = f"https://admin-icta.nitb.gov.pk/idp/applications?keyword=&from={today}&to={today}&status=6"
    page = nitb_session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    updated = []
    for tr in soup.find_all("tr"):
        for links in tr.find_all("a", href=True):
            pos = links.attrs["href"].find("/application/")
            if pos != -1:
                app_id = links.attrs["href"][pos + 13 :]
                th = threading.Thread(target=idp_update, args=(app_id,))
                th.start()
                updated.append(app_id)

    return {"message": "Update triggered", "apps": updated}


# ✅ Function to update one IDP
def idp_update(app_id: str) -> int:
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
        if not nitb_session:
            raise HTTPException(status_code=500, detail="Unable to connect to NITB")

    url = f"https://admin-icta.nitb.gov.pk/idp/application/{app_id}"
    page = nitb_session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    app_id_value, token = None, None
    for links in soup.find_all("input", type="hidden"):
        if links.attrs["name"] == "application_id":
            app_id_value = links.attrs["value"]
        elif links.attrs["name"] == "_token":
            token = links.attrs["value"]

    if not token or not app_id_value:
        raise HTTPException(status_code=500, detail="could not locate application id or token")

    update_url = "https://admin-icta.nitb.gov.pk/idp/application/status/update"
    params = {
        "_token": token,
        "application_id": app_id_value,
        "application_status_id": "8",
        "remarks": "Ok",
        "submit": "update",
    }
    response = nitb_session.post(update_url, data=params)
    print(response.status_code)
    return response.status_code


# ✅ Approve a specific application
@router.post("/approve/{app_id}")
def approve_idp(app_id: str):
    print(app_id)
    status = idp_update(app_id)
    if status == 200:
        print(status)
        return {"message": "Application Approved", "app_id": app_id}
    raise HTTPException(status_code=500, detail="Error approving application")


# ✅ Profile endpoint (return Passport link)
@router.get("/profile/{app_id}")
def profile(app_id: int):
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
        if not nitb_session:
            raise HTTPException(status_code=500, detail="Unable to connect to NITB")

    url = f"{config.NITB_BASE}/idp/application/{app_id}"
    page = nitb_session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    img = None
    for link in soup.find_all("a", href=True):
        if "Passport" in link.text:
            img = link.attrs["href"]
            break

    if not img:
        raise HTTPException(status_code=404, detail="Passport not found")

    return {"app_id": app_id, "passport_image": img}


# ✅ IDP home (search by keyword)
@router.get("/home")
def idp_home(keyword: Optional[str] = Query("", description="Search keyword")):
    records = load(keyword)
    return {"records": records}