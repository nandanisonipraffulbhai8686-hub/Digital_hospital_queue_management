from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_invoice(token_no, amount, status):
    file_name = f"invoice_{token_no}.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, 800, "Hospital Invoice")

    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Token Number : {token_no}")
    c.drawString(100, 720, f"Amount       : Rs. {amount}")
    c.drawString(100, 690, f"Status       : {status}")

    c.drawString(100, 650, "Thank you for choosing our hospital.")

    c.save()
    return file_name
