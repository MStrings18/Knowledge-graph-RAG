def generate_pdf(data: dict) -> str:
    file_path = f"/Users/akshitagrawal/Knowledge-graph-RAG/pdfs/{data['ref_id']}.pdf"
    # Generate a simple PDF using reportlab or any library
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from uuid import uuid4
    
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(file_path, pagesize=letter)
    c.drawString(100, 750, f"Document for ref_id: {data['ref_id']}")
    c.drawString(100, 735, f"Content: {data.get('content', 'No content')}")
    c.save()
    
    return file_path  # return the local file path
