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
def check_session():
    global nitb_session
    if nitb_session is None:
        nitb_session = get_session()
        return

    test_url = "https://admin-icta.nitb.gov.pk"
    response = nitb_session.get(test_url)

    if response.status_code == 200 and response.url != "https://admin-icta.nitb.gov.pk/login":
        return True
    else:
        nitb_session = get_session()
        return nitb_session is not False

def approve(url, status, **args):
    global nitb_session

    if nitb_session is None:
        nitb_session = get_session()

    if status not in ("arms-approval", "arms-deliver", "domicile-approval"):
        return {
            "success": False,
            "code": "INVALID_STATUS",
            "message": "Invalid approval status provided"
        }

    try:
        if status == "arms-approval":
            # Normalize URL
            show_url = url.replace("/edit", "/show") if "/show" not in url else url

            check_session()

            details_page = nitb_session.get(show_url)
            if details_page.status_code != 200:
                return {
                    "success": False,
                    "code": "DETAILS_FETCH_FAILED",
                    "message": "Failed to load application details page"
                }

            details_soup = BeautifulSoup(details_page.content, "html.parser")

            # Extract CSRF token
            token_input = details_soup.find("input", {"type": "hidden"})
            if not token_input:
                return {
                    "success": False,
                    "code": "TOKEN_NOT_FOUND",
                    "message": "CSRF token not found on details page"
                }

            token = token_input.get("value")

            # Renewal validation
            if args.get("request_type") == "Renewal":
                request_type = None

                for row in details_soup.find_all("div", class_="row"):
                    label = row.find("div", class_="text-muted")
                    if label and "Request Type" in label.get_text(strip=True):
                        value_div = label.find_next_sibling("div")
                        request_type = value_div.get_text(strip=True)
                        break

                if not request_type:
                    return {
                        "success": False,
                        "code": "REQUEST_TYPE_NOT_FOUND",
                        "message": "Request type not found on page"
                    }

                if not request_type.startswith("Renewal"):
                    return {
                        "success": False,
                        "code": "NOT_RENEWAL",
                        "message": f"Request type is '{request_type}', not Renewal"
                    }

            update_url = show_url.replace("/show", "") + "/status/update"

            params = {
                "_token": token,
                "application_status_id": "8",
                "remarks": "Ok",
                "submit": "update",
            }

            response = nitb_session.post(update_url, data=params)

        elif status == "arms-deliver":  # deliver
            deliver_url = url.replace("/edit", "/deliver")
            response = nitb_session.get(deliver_url)
        elif status == "domicile-approval":  # domicile approval
            check_session()

            details_page = nitb_session.get(url)
            if details_page.status_code != 200:
                return {
                    "success": False,
                    "code": "DETAILS_FETCH_FAILED",
                    "message": "Failed to load domicile details page"
                }

            details_soup = BeautifulSoup(details_page.content, "html.parser")

            # Extract CSRF token
            for input in details_soup.find_all("input", {"type": "hidden"}):
                if input.attrs['name'] == '_token':
                    token = input.attrs['value']
                if input.attrs['name'] == 'application_id':
                        application_id = input.attrs['value']    

            if not token or not application_id:
                return {
                    "success": False,
                    "code": "TOKEN_NOT_FOUND",
                    "message": "CSRF token or Application ID not found on details page"
                }
            
            update_url = "https://admin-icta.nitb.gov.pk/domicile/application/status/update"

            params = {
                "_token": token,
                "application_id": application_id,
                "application_status_id": "8",
                "remarks": "Approved",
                "submit": "update",
            }

            response = nitb_session.post(update_url, data=params)
        # Final validation
        if response.status_code != 200:
            return {
                "success": False,
                "code": "HTTP_ERROR",
                "message": f"Server returned status {response.status_code}"
            }

        if "login" in response.url:
            return {
                "success": False,
                "code": "SESSION_EXPIRED",
                "message": "Session expired, login required"
            }

        return {
            "success": True,
            "code": "APPROVED",
            "message": "Application approved successfully"
        }

    except Exception as e:
        return {
            "success": False,
            "code": "EXCEPTION",
            "message": str(e)
        }

