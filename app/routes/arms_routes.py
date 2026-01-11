from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import open_arms_con
from app.nitb import approve

# 🔐 Protect entire router
router = APIRouter(
    dependencies=[Depends(get_current_user)]
)


class ApproveUrlRequest(BaseModel):
    url: str


@router.get("/")
def list_pending():
    con, cur = open_arms_con()
    if type(con) is str:
        raise HTTPException(status_code=500, detail=cur)

    cur.execute("""
        SELECT * 
        FROM approver_app.need_approvals 
        WHERE file_status = 'Pending' 
        ORDER BY id DESC;
    """)
    data = cur.fetchall()

    cur.close()
    con.close()
    return {"data": data}


@router.post("/approve/{id}")
def approve_request(id: int):
    con, cur = open_arms_con()

    cur.execute("SELECT url FROM need_approvals WHERE id = %s;", (id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        con.close()
        raise HTTPException(status_code=404, detail="Record not found")

    result = approve(row["url"], "arms-approval")
    if not result or not result.get("success", True):
        cur.close()
        con.close()
        raise HTTPException(status_code=500, detail="NITB approval failed")

    cur.execute(
        "UPDATE need_approvals SET file_status='Approved', updated_at=%s WHERE id=%s;",
        (datetime.now(), id)
    )
    con.commit()

    cur.close()
    con.close()
    return {"status": "success", "message": f"Request {id} approved"}


@router.post("/approve-url")
def approve_url(payload: ApproveUrlRequest):
    result = approve(
        payload.url,
        "arms-approval",
        request_type="Renewal"
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/deliver/{id}")
def deliver_request(id: int):
    con, cur = open_arms_con()

    cur.execute("SELECT url FROM need_approvals WHERE id=%s;", (id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        con.close()
        raise HTTPException(status_code=404, detail="Record not found")

    result = approve(row["url"], "arms-deliver")
    if not result or not result.get("success", True):
        cur.close()
        con.close()
        raise HTTPException(status_code=500, detail="NITB delivery failed")

    cur.execute(
        "UPDATE need_approvals SET file_status='Approved', updated_at=%s WHERE id=%s;",
        (datetime.now(), id)
    )
    con.commit()

    cur.close()
    con.close()
    return {"status": "success", "message": f"Request {id} delivered"}


@router.post("/approve-all")
def approve_all():
    con, cur = open_arms_con()

    cur.execute("SELECT url FROM need_approvals WHERE file_status='Pending';")
    rows = cur.fetchall()

    approved_count = 0
    for row in rows:
        result = approve(row["url"], "arms-approval")
        if result and result.get("success", True):
            approved_count += 1

    cur.execute(
        "UPDATE need_approvals SET file_status='Approved', updated_at=%s WHERE file_status='Pending';",
        (datetime.now(),)
    )
    con.commit()

    cur.close()
    con.close()
    return {"status": "success", "approved_count": approved_count}


@router.post("/trash/{id}")
def trash_request(id: int):
    con, cur = open_arms_con()

    cur.execute(
        "UPDATE need_approvals SET file_status='Ignored' WHERE id=%s;",
        (id,)
    )
    con.commit()

    cur.close()
    con.close()
    return {"status": "success", "message": f"Request {id} ignored"}


@router.post("/trash-all")
def trash_all():
    con, cur = open_arms_con()

    cur.execute(
        "UPDATE need_approvals SET file_status='Ignored' WHERE file_status='Pending';"
    )
    con.commit()

    cur.close()
    con.close()
    return {"status": "success", "message": "All pending requests ignored"}


@router.get("/report")
def generate_report(
    report_date1: str = Query(..., description="Start date YYYY-MM-DD"),
    report_date2: str = Query(..., description="End date YYYY-MM-DD")
):
    con, cur = open_arms_con()

    cur.execute(
        """
        SELECT url, cnic, name, license_no, request_type
        FROM need_approvals
        WHERE DATE(updated_at) BETWEEN %s AND %s;
        """,
        (report_date1, report_date2)
    )
    records = cur.fetchall()

    cur.close()
    con.close()
    return {"count": len(records), "data": records}
