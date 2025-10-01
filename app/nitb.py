import requests
from bs4 import BeautifulSoup
from app import config

nitb_session = None

def get_session(id=config.NITB_ID, passw=config.NITB_PASS):
    global nitb_session
    nitb_session = requests.session()
    url = "https://admin-icta.nitb.gov.pk/login"

    try:
        page = nitb_session.get(url)
    except Exception as e:
        print("Connection Error", e)
        return False

    soup = BeautifulSoup(page.content, "html.parser")
    _token = None
    for links in soup.find_all("input", type="hidden"):
        _token = links.attrs["value"]
        break

    if not _token:
        print("No CSRF token found")
        return False

    payload = {"_token": _token, "email": id, "password": passw, "submit": "login"}
    response = nitb_session.post(url, data=payload)

    if response.url == "https://admin-icta.nitb.gov.pk/dashboard":
        print("✅ NITB session initialized")
        return nitb_session
    else:
        print("❌ Invalid credentials")
        return False


def approve(url, status):
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()

    if status == "approval":
        show_url = url.replace("/edit", "/show")
        details_page = nitb_session.get(show_url)
        details_soup = BeautifulSoup(details_page.content, "html.parser")
        token = None
        for links in details_soup.find_all("input", type="hidden"):
            token = links.attrs["value"]

        update_url = show_url.replace("/show", "") + "/status/update"
        params = {
            "_token": token,
            "application_status_id": "8",
            "remarks": "Ok",
            "submit": "update",
        }
        response = nitb_session.post(update_url, data=params)

    elif status == "deliver":
        deliver_url = url.replace("/edit", "/deliver")
        response = nitb_session.get(deliver_url)

    else:
        return False

    if response.status_code == 200 and response.url != "https://admin-icta.nitb.gov.pk/login":
        return True
    return False
