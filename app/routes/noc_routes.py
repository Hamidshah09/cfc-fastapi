import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, logger
from app import config
from app.auth import get_current_user
from app.database import open_con
from app.nitb import nitb_session, get_session
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/noc-ict", tags=["NOC ICT"])
class ApplicantIn(BaseModel):
    cnic: str
    name: str
    relation: str
    father_name: str

class LetterCreate(BaseModel):
    letter_date: str
    district: str
    remarks: str | None
    applicants: List[ApplicantIn]

@router.post("/letters")
def create_letter(data: LetterCreate, user=Depends(get_current_user)):
    
    con, cur = open_con()

    cur.execute(
        """INSERT INTO noc_ict_letters
           (Letter_Date, Letter_sent_to, Remarks)
           VALUES (%s,%s,%s)""",
        (data.letter_date, data.district, data.remarks)
    )
    con.commit()
    letter_id = cur.lastrowid

    # Dispatch number
    cur.execute(
        """SELECT Dispatch_No, YEAR(timestamp) y1, YEAR(CURDATE()) y2
           FROM dispatch_dairy ORDER BY Dispatch_ID DESC LIMIT 1"""
    )
    last = cur.fetchone()
    dispatch_no = 1 if not last or last["y1"] != last["y2"] else last["Dispatch_No"] + 1

    cur.execute(
        """INSERT INTO dispatch_dairy
           (Dispatch_No, Letter_Type, Letter_ID)
           VALUES (%s,'NOC ICT Letter',%s)""",
        (dispatch_no, letter_id)
    )
    con.commit()

    for a in data.applicants:
        cur.execute(
            """INSERT INTO noc_ict_applicants
               (Letter_ID,CNIC,Applicant_Name,Relation,Applicant_FName)
               VALUES (%s,%s,%s,%s,%s)""",
            (letter_id, a.cnic, a.name, a.relation, a.father_name)
        )
        con.commit()

    cur.close()
    con.close()

    return {"letter_id": letter_id, "dispatch_no": dispatch_no}

@router.get("/cnic-status/{cnic}")
def noc_cnic_status(
    cnic: str,
    user=Depends(get_current_user)
):
    clean_cnic = re.sub(r"\D", "", cnic)
    if len(clean_cnic) != 13:
        raise HTTPException(400, "CNIC must be 13 digits")

    con, cur = open_con()

    cur.execute(
        "SELECT reason FROM black_list WHERE cnic=%s AND status='Blocked'",
        (clean_cnic,)
    )
    black = cur.fetchone()

    cur.execute(
        "SELECT 1 FROM noc_applicants WHERE cnic=%s",
        (clean_cnic,)
    )
    other_dist = cur.fetchone()

    cur.execute(
        "SELECT 1 FROM noc_ict_applicants WHERE cnic=%s",
        (clean_cnic,)
    )
    ict = cur.fetchone()

    cur.close()
    con.close()

    return {
        "blacklisted": bool(black),
        "blacklist_reason": black["reason"] if black else None,
        "noc_other_district": bool(other_dist),
        "noc_ict": bool(ict)
    }
@router.get("/letters/{letter_id}")
def get_letter(
    letter_id: int,
    user=Depends(get_current_user)
):
    con, cur = open_con()

    cur.execute(
        """SELECT l.*, d.Dispatch_No,
                  a.App_ID, a.CNIC, a.Applicant_Name,
                  a.Relation, a.Applicant_FName
           FROM noc_ict_letters l
           JOIN dispatch_dairy d ON d.Letter_ID=l.Letter_ID
           LEFT JOIN noc_ict_applicants a ON a.Letter_ID=l.Letter_ID
           WHERE l.Letter_ID=%s
             AND d.Letter_Type='NOC ICT Letter'
           ORDER BY a.App_ID DESC""",
        (letter_id,)
    )
    rows = cur.fetchall()
    cur.close()
    con.close()

    if not rows:
        raise HTTPException(404, "Record not found")

    return rows
@router.get("/letters-search")
def search_letters(
    dispatch_no: int | None = None,
    cnic: str | None = None,
    date: str | None = None,
    user=Depends(get_current_user)
):
    con, cur = open_con()

    if dispatch_no is not None:
        Query = """SELECT l.Letter_ID, d.Dispatch_No, l.Letter_Date, l.Letter_sent_to, a.CNIC, a.Applicant_Name, a.Relation, a.Applicant_FName 
                            FROM noc_ict_letters as l 
                            Inner Join noc_ict_applicants as a
                            On l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where d.Dispatch_No = %s And d.Letter_Type = 'NOC ICT Letter' ORDER BY l.Letter_ID DESC Limit 50;"""
        cur.execute(Query, (dispatch_no,))
    elif cnic is not None:
        Query = """SELECT l.Letter_ID, d.Dispatch_No, l.Letter_Date, l.Letter_sent_to, a.CNIC, a.Applicant_Name, a.Relation, a.Applicant_FName 
                            FROM noc_ict_letters as l 
                            Inner Join noc_ict_applicants as a
                            on l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where a.CNIC = %s And d.Letter_Type = 'NOC ICT Letter' ORDER BY l.Letter_ID DESC Limit 50;"""
        cur.execute(Query, (cnic,))
    elif date is not None:
        Query = """SELECT l.Letter_ID, d.Dispatch_No, l.Letter_Date, l.Letter_Sent_to, a.CNIC, a.Applicant_Name, a.Relation, a.Applicant_FName 
                        FROM noc_ict_letters as l 
                        Inner Join noc_ict_applicants as a
                        On l.Letter_ID = a.Letter_ID
                        Inner Join dispatch_dairy as d
                        on d.Letter_ID = l.Letter_ID
                        Where l.Letter_Date = %s And d.Letter_Type = 'NOC ICT Letter' ORDER BY l.Letter_ID DESC Limit 50;"""
        cur.execute(Query, (date,))
    else:
        Query = """SELECT l.Letter_ID, d.Dispatch_No, l.Letter_Date, l.Letter_sent_to, a.CNIC, a.Applicant_Name, a.Relation, a.Applicant_FName 
                            FROM noc_ict_letters as l 
                            Inner Join noc_ict_applicants as a
                            on l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where d.Letter_Type = 'NOC ICT Letter' ORDER BY l.Letter_ID DESC Limit 50;"""
        cur.execute(Query)
    data = cur.fetchall()
    cur.close()
    con.close()

    return data
