from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.auth import get_current_user
from app.database import open_con
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io

router = APIRouter()


@router.get("/")
def generate_report(
    report_date1: str = Query(..., description="Start date (YYYY-MM-DD)"),
    report_date2: str = Query(..., description="End date (YYYY-MM-DD)"),
    user=Depends(get_current_user)
):
    con, cur = open_con()
    cur.execute(
        "SELECT url, cnic, name, license_no, request_type FROM need_approvals WHERE date(updated_at) BETWEEN %s AND %s;",
        (report_date1, report_date2),
    )
    records = cur.fetchall()
    cur.close()
    con.close()
    return {"count": len(records), "records": records}


@router.get("/pdf")
def generate_pdf_report(
    report_date1: str = Query(..., description="Start date (YYYY-MM-DD)"),
    report_date2: str = Query(..., description="End date (YYYY-MM-DD)"),
    user=Depends(get_current_user)
):
    con, cur = open_con()
    cur.execute(
        "SELECT cnic, name, license_no, request_type FROM need_approvals WHERE date(updated_at) BETWEEN %s AND %s;",
        (report_date1, report_date2),
    )
    records = cur.fetchall()
    cur.close()
    con.close()

    # Create PDF in memory
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    # Title
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(120, 750, f"Approved Files Report From {report_date1} to {report_date2}")

    # Table headers
    headers = ["S.No", "CNIC", "Name", "License No", "Request Type"]
    x_positions = [50, 100, 180, 350, 480]
    y_position = 720

    pdf.setFillColor(colors.lightgrey)
    pdf.rect(45, y_position - 5, 530, 20, fill=True, stroke=False)
    pdf.setFillColor(colors.black)

    pdf.setFont("Helvetica-Bold", 12)
    for i, header in enumerate(headers):
        pdf.drawString(x_positions[i], y_position, header)

    # Table rows
    pdf.setFont("Helvetica", 10)
    y_position -= 20
    sl = 0
    bottom_margin = 50

    for record in records:
        sl += 1
        if y_position < bottom_margin:
            pdf.showPage()
            y_position = 720
            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColor(colors.lightgrey)
            pdf.rect(45, y_position - 5, 530, 20, fill=True, stroke=False)
            pdf.setFillColor(colors.black)
            for i, header in enumerate(headers):
                pdf.drawString(x_positions[i], y_position, header)
            y_position -= 20
            pdf.setFont("Helvetica", 10)

        pdf.drawString(x_positions[0], y_position, str(sl))
        pdf.drawString(x_positions[1], y_position, str(record["cnic"]))
        pdf.drawString(x_positions[2], y_position, str(record["name"]))
        pdf.drawString(x_positions[3], y_position, str(record["license_no"]))
        pdf.drawString(x_positions[4], y_position, str(record["request_type"]))
        y_position -= 20

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{report_date1}_to_{report_date2}.pdf"}
    )
