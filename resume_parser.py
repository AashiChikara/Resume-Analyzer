import fitz  # this is PyMuPDF's import name


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Take raw PDF bytes and return the extracted text.
    Raises ValueError with a clear message if something is wrong.
    """
    try:
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        raise ValueError("The uploaded file is not a valid PDF.")

    if pdf.page_count == 0:
        raise ValueError("The PDF has no pages.")

    text_parts = []
    for page in pdf:
        text_parts.append(page.get_text())

    pdf.close()

    full_text = "\n".join(text_parts).strip()

    if not full_text:
        raise ValueError(
            "No readable text found in this PDF. "
            "It may be a scanned image without selectable text."
        )

    return full_text