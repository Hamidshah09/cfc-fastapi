import logging
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
import requests
import json
router = APIRouter()
logger = logging.getLogger(__name__)

from app.nitb import nitb_get

@router.get("/check-in-nitb/{cnic}")
def check_in_nitb(cnic: int):

    try:

        url = (
            "https://admin-icta.nitb.gov.pk/"
            f"domicile/applications?keyword={cnic}"
            "&from=&to=&status="
        )

        response = nitb_get(url)

        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        full_data = []

        notfound = soup.find(
            "div",
            class_="empty-state"
        )

        if notfound:

            return {
                "status": "success",
                "records": 0,
                "message": "No record found",
                "data": []
            }

        for links in soup.find_all(
            "a",
            href=True,
            class_="btn-eye"
        ):

            data_link = links["href"]

            details_page = nitb_get(data_link)

            details_soup = BeautifulSoup(
                details_page.content,
                "html.parser"
            )

            data_dict = {}

            for details_div in details_soup.find_all(
                "div",
                class_="app-info-cell"
            ):

                lbl = details_div.find(
                    "div",
                    class_="app-info-lbl"
                )

                val = details_div.find(
                    "div",
                    class_="app-info-val"
                )

                if lbl and val:

                    data_dict[
                        lbl.text.strip()
                    ] = val.text.strip()

            for details_div in details_soup.find_all(
                "div",
                class_="app-field-item"
            ):

                lbl = details_div.find(
                    "div",
                    class_="app-field-lbl"
                )

                val = details_div.find(
                    "div",
                    class_="app-field-val"
                )

                if lbl and val:

                    data_dict[
                        lbl.text.strip()
                    ] = val.text.strip()

            full_data.append(data_dict)

        return {
            "status": "success",
            "records": len(full_data),
            "message": "Record found",
            "data": full_data
        }

    except requests.exceptions.Timeout:

        logger.exception(
            f"NITB timeout for CNIC: {cnic}"
        )

        raise HTTPException(
            status_code=504,
            detail="NITB server timeout"
        )

    except Exception as e:

        logger.exception(
            f"NITB error: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/check-in-other-district/{cnic}")
def check_in_other_district(cnic: int):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        """
        ----------------------------------------------------------------------
        Punjab Domicile Checking
        ----------------------------------------------------------------------
        """

        punjab_url = (
            f"https://domicile.punjab.gov.pk/AjaxCall.aspx?ID={cnic}"
        )

        logger.info(f"Checking Punjab domicile for CNIC: {cnic}")

        response = requests.get(
            punjab_url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        domicile_status = soup.find("span", {"id": "lblStatus"})

        if domicile_status and domicile_status.text.strip():

            dom_name = soup.find("span", {"id": "lblName"})

            applicant_name = (
                dom_name.text.strip()
                if dom_name
                else "Unknown"
            )

            logger.info(
                f"Punjab domicile found for CNIC: {cnic}"
            )

            return {
                "status": "success",
                "source": "Punjab",
                "found": True,
                "message": "Domicile record found in Punjab",
                "data": {
                    "name": applicant_name,
                    "status": domicile_status.text.strip()
                }
            }

    except requests.exceptions.Timeout:

        logger.error(
            f"Punjab API timeout for CNIC: {cnic}"
        )

    except requests.exceptions.RequestException as e:

        logger.error(
            f"Punjab API request error: {str(e)}"
        )

    except Exception as e:

        logger.exception(
            f"Punjab processing error: {str(e)}"
        )

    try:

        """
        ----------------------------------------------------------------------
        KPK Domicile Checking
        ----------------------------------------------------------------------
        """

        kpk_url = (
            "https://cfc.kp.gov.pk/Domicile/"
            f"Domicile/GetDomicileVerificationDetail?cnicDomNo={cnic}"
        )

        logger.info(f"Checking KPK domicile for CNIC: {cnic}")

        response = requests.get(
            kpk_url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        logger.info(
            f"KPK Raw Response: {response.text}"
        )

        # IMPORTANT FIX
        # Sometimes API returns JSON string instead of object

        kp_dom_data = response.json()

        if isinstance(kp_dom_data, str):

            logger.warning(
                "KPK API returned JSON string. Parsing again."
            )

            kp_dom_data = json.loads(kp_dom_data)

        if not isinstance(kp_dom_data, dict):

            logger.error(
                f"Unexpected KPK response type: {type(kp_dom_data)}"
            )

            raise HTTPException(
                status_code=502,
                detail="Invalid response from KPK server"
            )

        track_list = kp_dom_data.get("TrackListData", [])

        if isinstance(track_list, list) and len(track_list) > 0:

            record = track_list[0]

            logger.info(
                f"KPK domicile found for CNIC: {cnic}"
            )

            return {
                "status": "success",
                "source": "KPK",
                "found": True,
                "message": "Domicile record found in KPK",
                "data": {
                    "name": record.get("Dom_Name"),
                    "status": record.get("DomicileStatus"),
                    "date": record.get(
                        "DomicileStatusDateFormatted"
                    ),
                    "district": record.get("DistrictName"),
                    "tehsil": record.get("TehsilName"),
                    "domicile_no": record.get("domicileNo")
                }
            }

    except requests.exceptions.Timeout:

        logger.error(
            f"KPK API timeout for CNIC: {cnic}"
        )

    except requests.exceptions.RequestException as e:

        logger.error(
            f"KPK API request error: {str(e)}"
        )

    except json.JSONDecodeError as e:

        logger.error(
            f"KPK JSON decode error: {str(e)}"
        )

    except Exception as e:

        logger.exception(
            f"KPK processing error: {str(e)}"
        )

    """
    --------------------------------------------------------------------------
    No Record Found
    --------------------------------------------------------------------------
    """

    logger.info(
        f"No domicile found for CNIC: {cnic}"
    )

    return {
        "status": "success",
        "found": False,
        "message": "No domicile record found"
    }

from fastapi import HTTPException
from bs4 import BeautifulSoup
import requests
import re

from app.nitb import nitb_get
from app import config


@router.get("/statistics/check")
def statistics():

    try:

        url = f"{config.NITB_BASE}/dashboard/statistics"

        logger.info(
            "Fetching NITB statistics"
        )

        response = nitb_get(url)

        logger.info(
            f"Statistics page fetched successfully "
            f"(length={len(response.content)})"
        )

        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        details = {
            "domicile": 0,
            "idp": 0
        }

        cards = soup.find_all(
            "div",
            class_="bd-highlight"
        )

        logger.info(
            f"Found {len(cards)} statistic cards"
        )

        for div in cards:

            text = div.get_text(
                separator=" ",
                strip=True
            )

            logger.debug(
                f"Statistics raw text: {text}"
            )

            # Extract number safely
            number_match = re.search(
                r"\b\d+\b",
                text
            )

            value = (
                int(number_match.group())
                if number_match
                else 0
            )

            text_lower = text.lower()

            if "domicile" in text_lower:

                details["domicile"] = value

            elif "idp" in text_lower:

                details["idp"] = value

        logger.info(
            f"Statistics extracted: {details}"
        )

        return {
            "status": "success",
            "message": "Statistics fetched successfully",
            "data": details
        }

    except requests.exceptions.Timeout:

        logger.exception(
            "NITB statistics timeout"
        )

        raise HTTPException(
            status_code=504,
            detail="NITB server timeout"
        )

    except requests.exceptions.HTTPError as e:

        logger.exception(
            f"NITB HTTP error: {str(e)}"
        )

        raise HTTPException(
            status_code=502,
            detail="Failed to fetch NITB statistics"
        )

    except Exception as e:

        logger.exception(
            f"Statistics processing error: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )