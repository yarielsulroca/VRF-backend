from vrf.adapters.outbound.ocr.pdf import extract_pdf_text


def _make_pdf(text: str) -> bytes:
    esc = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 12 Tf 72 720 Td ({esc}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
    out += str(xref_pos).encode() + b"\n%%EOF\n"
    return bytes(out)


def test_extract_pdf_text_devuelve_texto(tmp_path) -> None:
    pdf = _make_pdf("FACTURA A 0001-00012345")
    path = tmp_path / "muestra.pdf"
    path.write_bytes(pdf)

    texto = extract_pdf_text(str(path))

    assert "FACTURA A 0001-00012345" in texto


def test_extract_pdf_text_pdf_vacio(tmp_path) -> None:
    pdf = _make_pdf("")
    path = tmp_path / "vacio.pdf"
    path.write_bytes(pdf)

    assert extract_pdf_text(str(path)) == ""