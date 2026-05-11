import logging
import requests

from bs4 import BeautifulSoup
from app import config

logger = logging.getLogger(__name__)

BASE_URL = "https://admin-icta.nitb.gov.pk"

nitb_session = None


def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    return session


def login_nitb(
    user_id=config.NITB_ID,
    password=config.NITB_PASS
):

    global nitb_session

    try:

        nitb_session = create_session()

        login_url = f"{BASE_URL}/login"

        page = nitb_session.get(
            login_url,
            timeout=20
        )

        page.raise_for_status()

        soup = BeautifulSoup(
            page.content,
            "html.parser"
        )

        token_input = soup.find(
            "input",
            {"name": "_token"}
        )

        if not token_input:

            logger.error(
                "NITB login token not found"
            )

            return False

        token = token_input.get("value")

        payload = {
            "_token": token,
            "email": user_id,
            "password": password,
            "submit": "login"
        }

        response = nitb_session.post(
            login_url,
            data=payload,
            timeout=20,
            allow_redirects=True
        )

        if "/dashboard" not in response.url:

            logger.error(
                "NITB login failed"
            )

            nitb_session = None

            return False

        logger.info(
            "NITB login successful"
        )

        return True

    except Exception as e:

        logger.exception(
            f"NITB login error: {str(e)}"
        )

        nitb_session = None

        return False


def is_session_valid():

    global nitb_session

    if nitb_session is None:
        return False

    try:

        response = nitb_session.get(
            f"{BASE_URL}/dashboard",
            timeout=15,
            allow_redirects=False
        )

        if response.status_code in [301, 302]:
            return False

        if "/login" in response.text.lower():
            return False

        if response.status_code != 200:
            return False

        return True

    except Exception as e:

        logger.exception(
            f"Session validation failed: {str(e)}"
        )

        return False


def ensure_session():

    if is_session_valid():
        return True

    logger.warning(
        "NITB session expired. Re-logging."
    )

    return login_nitb()


def nitb_get(url, **kwargs):

    global nitb_session

    if not ensure_session():

        raise Exception(
            "Unable to establish NITB session"
        )

    response = nitb_session.get(
        url,
        timeout=20,
        **kwargs
    )

    # Auto retry if session expired suddenly
    if "/login" in response.url:

        logger.warning(
            "Session expired during request. Retrying."
        )

        if not login_nitb():

            raise Exception(
                "NITB re-login failed"
            )

        response = nitb_session.get(
            url,
            timeout=20,
            **kwargs
        )

    response.raise_for_status()

    return response


def nitb_post(url, **kwargs):

    global nitb_session

    if not ensure_session():

        raise Exception(
            "Unable to establish NITB session"
        )

    response = nitb_session.post(
        url,
        timeout=20,
        **kwargs
    )

    if "/login" in response.url:

        logger.warning(
            "Session expired during POST request. Retrying."
        )

        if not login_nitb():

            raise Exception(
                "NITB re-login failed"
            )

        response = nitb_session.post(
            url,
            timeout=20,
            **kwargs
        )

    response.raise_for_status()

    return response