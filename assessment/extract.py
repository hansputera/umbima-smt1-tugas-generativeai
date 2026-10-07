"""Port of src/lib/grading/extract.ts: pdf (pypdf) / docx (python-docx)."""

from io import BytesIO


def extract_file_text(name, data):
    """Return {"ok": True, "text": ...} or {"ok": False, "message": ...}."""
    lower = (name or "").lower()
    try:
        if lower.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        elif lower.endswith(".docx"):
            from docx import Document

            doc = Document(BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            return {"ok": False, "message": "Teks tidak terbaca."}
    except Exception:  # noqa: BLE001 - Node catches every extraction error
        return {"ok": False, "message": "Teks tidak terbaca."}
    clean = (text or "").strip()
    if not clean:
        return {"ok": False, "message": "Teks tidak terbaca."}
    return {"ok": True, "text": clean}
