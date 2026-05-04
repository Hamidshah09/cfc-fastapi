import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, logger
from app import config
from app.auth import get_current_user
from app.database import open_con
from app.nitb import nitb_session, get_session
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, date

router = APIRouter(prefix="/verification", tags=["Verification"])
class ApplicantIn(BaseModel):
    cnic: str
    name: str
    relation: str
    father_name: str
    address:str
    domicile_no:str
    domicile_date:date

class LetterCreate(BaseModel):
    letter_date: date
    letter_no: str = Field(max=75)
    letter_sent_by:str = Field(max=70)
    designation:str = Field(max=70)
    sender_address:str = Field(max=150)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    remarks: str | None
    applicants: List[ApplicantIn]

@router.post("/letters")
def create_letter(data: LetterCreate, user=Depends(get_current_user)):
    
    con, cur = open_con()

    cur.execute("Insert Into verification_letters (Letter_Date, Letter_No, Letter_Sent_by, Designation, sender_address, Remarks) values (%s,%s, %s,%s, %s, %s);",
            (data.letter_date, data.letter_no, data.letter_sent_by, data.designation, data.sender_address, data.remarks))
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
           VALUES (%s,'Verification Letter',%s)""",
        (dispatch_no, letter_id)
    )
    con.commit()

    for a in data.applicants:
        cur.execute(
            """INSERT INTO verification_applicants
               (Letter_ID,CNIC,Applicant_Name,Relation,Applicant_FName, address, domicile_no, domicile_date)
               VALUES (%s,%s,%s,%s,%s,%s,%s, %s)""",
            (letter_id, a.cnic, a.name, a.relation, a.father_name, a.address, a.domicile_no, a.domicile_date)
        )
        con.commit()

    cur.close()
    con.close()

    return {"letter_id": letter_id, "dispatch_no": dispatch_no}

@router.get("/letters-search")
def search_letters(
    dispatch_no: int | None = None,
    id:int | None = None,
    cnic: str | None = None,
    date: str | None = None,
    user=Depends(get_current_user)
):
    con, cur = open_con()

    if dispatch_no is not None:
        Query = """SELECT l.*, d.Dispatch_No, a.* 
                            FROM verification_letters as l 
                            Inner Join verification_applicants as a
                            On l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where d.Dispatch_No = %s And d.Letter_Type = 'Verification Letter' order by l.Letter_ID desc;"""
        cur.execute(Query, (dispatch_no,))
    elif id is not None:
        Query = """SELECT l.*, d.Dispatch_No, a.* 
                            FROM verification_letters as l 
                            Inner Join verification_applicants as a
                            On l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where l.Letter_ID = %s And d.Letter_Type = 'Verification Letter' order by l.Letter_ID desc;"""
        cur.execute(Query, (id,))
    elif cnic is not None:
        Query = """SELECT l.*, d.Dispatch_No, a.* 
                            FROM verification_letters as l 
                            Inner Join verification_applicants as a
                            on l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where a.CNIC = %s And d.Letter_Type = 'Verification Letter' order by l.Letter_ID desc;"""
        cur.execute(Query, (cnic,))
    elif date is not None:
        Query = """SELECT l.*, d.Dispatch_No, a.* 
                        FROM verification_letters as l 
                        Inner Join verification_applicants as a
                        On l.Letter_ID = a.Letter_ID
                        Inner Join dispatch_dairy as d
                        on d.Letter_ID = l.Letter_ID
                        Where l.Letter_Date = %s And d.Letter_Type = 'Verification Letter' order by l.Letter_ID desc;"""
        cur.execute(Query, (date,))
    else:
        Query = """SELECT l.*, d.Dispatch_No, a.* 
                            FROM verification_letters as l 
                            Inner Join verification_applicants as a
                            on l.Letter_ID = a.Letter_ID
                            Inner Join dispatch_dairy as d
                            on d.Letter_ID = l.Letter_ID
                            Where d.Letter_Type = 'Verification Letter' order by l.Letter_ID desc limit 100;"""
        cur.execute(Query)
    data = cur.fetchall()
    cur.close()
    con.close()

    return data
@router.get("/letters/{letter_id}")
def get_letter(
    letter_id: int,
    user=Depends(get_current_user)
):
    print("Letter ID received:", letter_id)
    con, cur = open_con()

    cur.execute(
        """SELECT l.*, d.Dispatch_No, a.*
           FROM verification_letters l
           JOIN dispatch_dairy d ON d.Letter_ID=l.Letter_ID
           LEFT JOIN verification_applicants a ON a.Letter_ID=l.Letter_ID
           WHERE l.Letter_ID=%s
             AND d.Letter_Type='Verification Letter'
           ORDER BY a.App_ID""",
        (letter_id,)
    )
    rows = cur.fetchall()
    cur.close()
    con.close()
    print(rows)
    if not rows:
        raise HTTPException(404, "Record not found")
    else:
        applicants = []
        for row in rows:
            applicants.append({
                "App_ID": row["App_ID"],
                "CNIC": row["CNIC"],
                "Applicant_Name": row["Applicant_Name"],
                "Relation": row["Relation"],
                "Applicant_FName": row["Applicant_FName"],
                "Domicile_No": row["Domicile_No"],
                "Domicile_Date": row["Domicile_Date"],
                "address": row["address"]
            })
        record = {
            "Letter_ID": rows[0]["Letter_ID"],
            "Letter_Date": rows[0]["Letter_Date"],
            "Letter_No": rows[0]["Letter_No"],
            "Letter_Sent_by": rows[0]["Letter_Sent_by"],
            "Designation": rows[0]["Designation"],
            "sender_address": rows[0]["Sender_Address"],
            "Remarks": rows[0]["Remarks"],
            "Dispatch_No": rows[0]["Dispatch_No"],
            "Applicants": applicants}
    return record

@router.get("/already-exists/{cnic}")
def get_letter(
    cnic: int,
    user=Depends(get_current_user)
):
    con, cur = open_con()
    cur.execute(
        """SELECT l.*, d.Dispatch_No,
                  a.App_ID, a.CNIC, a.Applicant_Name,
                  a.Relation, a.Applicant_FName, a.domicile_no, a.domicile_date
           FROM verification_letters l
           JOIN dispatch_dairy d ON d.Letter_ID=l.Letter_ID
           JOIN verification_applicants a ON a.Letter_ID=l.Letter_ID
           WHERE a.CNIC=%s
             AND d.Letter_Type='Verification Letter'""",
        (cnic,)
    )
    rows = cur.fetchall()
    cur.close()
    if not rows:
        return {"exists": False}
    else:
        return {"exists": True, "data": rows}