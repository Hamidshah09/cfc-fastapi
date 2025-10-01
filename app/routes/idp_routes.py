from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import open_con
from app.nitb import approve
from datetime import datetime

router = APIRouter()

@router.get("/")
def list_pending(user=Depends(get_current_user)):
    con, cur = open_con()
    if type(con) is str:
        raise HTTPException(status_code=500, detail=cur)

    cur.execute("SELECT * FROM need_approvals WHERE file_status='Pending' ORDER BY id DESC;")
    data = cur.fetchall()
    cur.close()
    con.close()
    return {"count": len(data), "data": data}


@router.post("/approve/{id}")
def approve_request(id: int, user=Depends(get_current_user)):
    con, cur = open_con()
    cur.execute("SELECT url FROM need_approvals WHERE id=%s;", (id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    if not approve(row["url"], "approval"):
        raise HTTPException(status_code=500, detail="NITB approval failed")

    cur.execute("UPDATE need_approvals SET file_status='Approved', updated_at=%s WHERE id=%s;", (datetime.now(), id))
    con.commit()
    cur.close()
    con.close()
    return {"status": "success", "message": f"Request {id} approved"}


@router.post("/deliver/{id}")
def deliver_request(id: int, user=Depends(get_current_user)):
    con, cur = open_con()
    cur.execute("SELECT url FROM need_approvals WHERE id=%s;", (id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    if not approve(row["url"], "deliver"):
        raise HTTPException(status_code=500, detail="NITB delivery failed")

    cur.execute("UPDATE need_approvals SET file_status='Approved', updated_at=%s WHERE id=%s;", (datetime.now(), id))
    con.commit()
    cur.close()
    con.close()
    return {"status": "success", "message": f"Request {id} delivered"}


@router.post("/approve-all")
def approve_all(user=Depends(get_current_user)):
    con, cur = open_con()
    cur.execute("SELECT url FROM need_approvals WHERE file_status='Pending';")
    rows = cur.fetchall()

    approved_count = 0
    for row in rows:
        if approve(row["url"], "approval"):
            approved_count += 1

    cur.execute("UPDATE need_approvals SET file_status='Approved', updated_at=%s WHERE file_status='Pending';", (datetime.now(),))
    con.commit()
    cur.close()
    con.close()
    return {"status": "success", "approved_count": approved_count}


@router.post("/trash/{id}")
def trash_request(id: int, user=Depends(get_current_user)):
    con, cur = open_con()
    cur.execute("UPDATE need_approvals SET file_status='Ignored' WHERE id=%s;", (id,))
    con.commit()
    cur.close()
    con.close()
    return {"status": "success", "message": f"Request {id} ignored"}


@router.post("/trash-all")
def trash_all(user=Depends(get_current_user)):
    con, cur = open_con()
    cur.execute("UPDATE need_approvals SET file_status='Ignored' WHERE file_status='Pending';")
    con.commit()
    cur.close()
    con.close()
    return {"status": "success", "message": "All pending requests ignored"}

@router.get("/report")
def generate_report(report_date1: str, report_date2: str, user=Depends(get_current_user)):
    con, cur = open_con()
    cur.execute("SELECT url, cnic, name, license_no, request_type FROM need_approvals WHERE date(updated_at) BETWEEN %s AND %s;", 
                (report_date1, report_date2))
    records = cur.fetchall()
    cur.close()
    con.close()
    return {"count": len(records), "records": records}