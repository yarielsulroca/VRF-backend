"""OCR de fotos y PDFs escaneados con Tesseract.

Los PDF con texto embebido se leen con pypdf (ver `pdf.py`), que es exacto y barato.
Esto es el camino lento, solo para cuando no hay texto que leer.
"""

from __future__ import annotations

from io import BytesIO

try:
    import pypdfium2
    import pytesseract
    from PIL import Image, ImageOps

    _IMPORTADO = True
except ImportError:  # pragma: no cover - entorno sin las dependencias de OCR
    _IMPORTADO = False

_IDIOMAS = ("spa+eng", "spa", "eng")
# Original / duplicado / triplicado repiten la misma factura: con las primeras alcanza.
_MAX_PAGINAS = 2
# ~216 DPI: suficiente para el cuerpo de una factura sin disparar la memoria.
_ESCALA_PDF = 3
# Tesseract pierde precisión con imágenes chicas y se vuelve lento con las enormes.
_ANCHO_MINIMO = 1600
_ANCHO_MAXIMO = 4000
_TIMEOUT_SEGUNDOS = 60


def ocr_disponible() -> bool:
    """El binario de Tesseract es opcional: sin él el preview queda vacío, no rompe."""
    if not _IMPORTADO:
        return False
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def _enderezar(imagen: "Image.Image") -> "Image.Image":
    """Una factura de costado sale ilegible, así que Tesseract detecta el giro."""
    try:
        osd = pytesseract.image_to_osd(
            imagen, output_type=pytesseract.Output.DICT, timeout=_TIMEOUT_SEGUNDOS
        )
    except Exception:
        # Sin texto suficiente para decidir: la dejamos como vino.
        return imagen
    giro = int(osd.get("rotate", 0)) % 360
    # Tesseract informa los grados horarios a aplicar; PIL rota en antihorario.
    return imagen.rotate(-giro, expand=True) if giro else imagen


def _preparar(imagen: "Image.Image") -> "Image.Image":
    # Las fotos de celular guardan la rotación en EXIF en vez de aplicarla.
    imagen = ImageOps.exif_transpose(imagen)
    imagen = imagen.convert("L")
    imagen = _enderezar(imagen)
    ancho, alto = imagen.size
    if ancho < _ANCHO_MINIMO:
        factor = _ANCHO_MINIMO / ancho
    elif ancho > _ANCHO_MAXIMO:
        factor = _ANCHO_MAXIMO / ancho
    else:
        factor = 1.0
    if factor != 1.0:
        imagen = imagen.resize((round(ancho * factor), round(alto * factor)), Image.LANCZOS)
    return ImageOps.autocontrast(imagen)


def _leer(imagen: "Image.Image") -> str:
    for idioma in _IDIOMAS:
        try:
            return pytesseract.image_to_string(
                imagen, lang=idioma, timeout=_TIMEOUT_SEGUNDOS
            )
        except pytesseract.TesseractError:
            # Falta el paquete de ese idioma: probamos el siguiente.
            continue
        except RuntimeError:
            # Timeout de Tesseract: no tiene sentido reintentar con otro idioma.
            return ""
    return ""


def texto_de_imagen(data: bytes) -> str:
    if not ocr_disponible():
        return ""
    try:
        with Image.open(BytesIO(data)) as imagen:
            return _leer(_preparar(imagen))
    except Exception:
        return ""


def texto_de_pdf_escaneado(data: bytes) -> str:
    if not ocr_disponible():
        return ""
    try:
        pdf = pypdfium2.PdfDocument(data)
    except Exception:
        return ""
    partes: list[str] = []
    try:
        for indice in range(min(len(pdf), _MAX_PAGINAS)):
            pagina = pdf[indice]
            imagen = pagina.render(scale=_ESCALA_PDF).to_pil()
            try:
                partes.append(_leer(_preparar(imagen)))
            finally:
                imagen.close()
    except Exception:
        return "\n".join(partes)
    finally:
        pdf.close()
    return "\n".join(partes)
