"""Diagnóstico del OCR AFIP: muestra por qué camino se leyó el archivo,
el texto que se obtuvo y el parseo campo por campo.

Uso: python backend/tools/diag_ocr.py ruta/a/factura.pdf
     python backend/tools/diag_ocr.py ruta/a/foto.jpg
"""

from __future__ import annotations

import sys
import time
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vrf.adapters.outbound.ocr.adapter import _con_texto, _es_imagen, _es_pdf  # noqa: E402
from vrf.adapters.outbound.ocr.afip import parse_afip_text  # noqa: E402
from vrf.adapters.outbound.ocr.imagen import (  # noqa: E402
    ocr_disponible,
    texto_de_imagen,
    texto_de_pdf_escaneado,
)
from vrf.adapters.outbound.ocr.pdf import extract_pdf_text_bytes  # noqa: E402

_MIMES = {".pdf": "application/pdf", ".png": "image/png", ".webp": "image/webp"}


def _leer(data: bytes, mime: str) -> tuple[str, str]:
    if _es_pdf(data, mime):
        texto = extract_pdf_text_bytes(data)
        if _con_texto(texto):
            return "PDF con texto embebido (pypdf)", texto
        if not ocr_disponible():
            return "PDF escaneado, pero Tesseract NO está instalado", ""
        return "PDF escaneado (Tesseract)", texto_de_pdf_escaneado(data)
    if _es_imagen(data, mime):
        if not ocr_disponible():
            return "Imagen, pero Tesseract NO está instalado", ""
        return "Imagen (Tesseract)", texto_de_imagen(data)
    return "Formato no soportado", ""


def main(ruta: str) -> int:
    archivo = Path(ruta)
    data = archivo.read_bytes()
    mime = _MIMES.get(archivo.suffix.lower(), "image/jpeg")

    inicio = time.perf_counter()
    camino, texto = _leer(data, mime)
    tardo = time.perf_counter() - inicio

    print(f"=== CAMINO: {camino} — {tardo:.1f}s ===")
    print(f"\n=== TEXTO ({len(texto)} chars) ===")
    print(texto if texto.strip() else "<VACÍO>")

    print("\n=== PARSEO ===")
    resultado = parse_afip_text(texto)
    for campo in fields(resultado):
        valor = getattr(resultado, campo.name)
        marca = "   " if valor is not None else " ! "
        print(f"{marca}{campo.name:<14} {valor}")
    print(f"\nincompleto: {resultado.incompleto()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
