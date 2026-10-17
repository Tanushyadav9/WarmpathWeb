import io
import zipfile
import xml.etree.ElementTree as ET
from app.core.errors import AppError

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PAGE_COUNT = 5


def validate_magic_bytes(file_bytes: bytes) -> str:
    """
    Validates magic bytes to ensure file is genuinely a PDF or DOCX.
    Returns format string: 'pdf' or 'docx'.
    """
    if len(file_bytes) > MAX_FILE_SIZE:
        raise AppError(
            code="file_too_large",
            message=f"Resume file size exceeds maximum limit of 5 MB ({len(file_bytes)} bytes).",
            status_code=400,
        )

    # PDF Magic Bytes: %PDF- (0x25 0x50 0x44 0x46 0x2D)
    if file_bytes.startswith(b"%PDF-"):
        return "pdf"

    # DOCX Magic Bytes: PK\x03\x04 (zip archive) containing word/document.xml
    if file_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                namelist = zf.namelist()
                if "word/document.xml" in namelist:
                    return "docx"
        except Exception:
            pass

    raise AppError(
        code="invalid_file_format",
        message="Only genuine text-based PDF or DOCX documents are accepted.",
        status_code=400,
    )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text using pypdf with fallback to pdfplumber.
    Enforces max 5 page limit and detects scanned unreadable documents.
    """
    extracted_text = ""
    page_count = 0

    # 1. Primary: pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        page_count = len(reader.pages)
        if page_count > MAX_PAGE_COUNT:
            raise AppError(
                code="page_limit_exceeded",
                message=f"Resume has {page_count} pages, exceeding the maximum allowed limit of {MAX_PAGE_COUNT} pages.",
                status_code=400,
            )

        for page in reader.pages:
            text = page.extract_text() or ""
            extracted_text += text + "\n"
    except AppError:
        raise
    except Exception:
        # Fall back to pdfplumber
        pass

    # 2. Fallback: pdfplumber if pypdf got little or no text
    if len(extracted_text.strip()) < 50:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                page_count = len(pdf.pages)
                if page_count > MAX_PAGE_COUNT:
                    raise AppError(
                        code="page_limit_exceeded",
                        message=f"Resume has {page_count} pages, exceeding the maximum allowed limit of {MAX_PAGE_COUNT} pages.",
                        status_code=400,
                    )
                extracted_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    extracted_text += text + "\n"
        except AppError:
            raise
        except Exception:
            pass

    cleaned_text = extracted_text.strip()
    if len(cleaned_text) < 10:
        raise AppError(
            code="resume_unreadable",
            message="The uploaded document contains scanned image content with no extractable text. Please upload a standard text PDF or DOCX.",
            status_code=422,
        )

    return cleaned_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text content from a DOCX zip container."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            xml_content = zf.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            # Namespace for Word processing ML
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            texts = [node.text for node in tree.iterfind(".//w:t", ns) if node.text]
            cleaned_text = " ".join(texts).strip()

            if len(cleaned_text) < 50:
                raise AppError(
                    code="resume_unreadable",
                    message="The uploaded document contains insufficient or unreadable text.",
                    status_code=422,
                )
            return cleaned_text
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            code="docx_extraction_failed",
            message=f"Could not parse DOCX document: {str(e)}",
            status_code=422,
        )


def extract_resume_text(file_bytes: bytes) -> tuple[str, str]:
    """Validates format and extracts clean textual content."""
    doc_format = validate_magic_bytes(file_bytes)
    if doc_format == "pdf":
        text = extract_text_from_pdf(file_bytes)
    else:
        text = extract_text_from_docx(file_bytes)
    return doc_format, text
