import PyPDF2

def extract_pdf_text(file_obj):
    reader = PyPDF2.PdfReader(file_obj)
    pages = [page.extract_text() for page in reader.pages]
    return "\n\n".join(p for p in pages if p)
