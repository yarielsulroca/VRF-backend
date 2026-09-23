from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from vrf.domain.enums import TipoAfip
from vrf.domain.ports.ocr import OcrResultado
from vrf.domain.vos import cuit_valido

_CUIT = re.compile(r"\b(\d{2}-?\d{8}-?\d)\b")
_FACTURA = re.compile(r"\bFACTURA\s+([ABC])\b", re.I)
_PV_NRO = re.compile(r"\b(\d{4,5})\s*[-/]\s*(\d{1,8})\b")
_PV = re.compile(r"PUNTO\s+DE\s+VENTA\s*:?\s*(\d{1,5})", re.I)
_NRO = re.compile(r"(?:COMP(?:ROBANTE)?\.?\s*N(?:RO|UMERO|\.|°)?)\s*:?\s*(\d{1,8})", re.I)
_COMP_NRO = re.compile(r"Comp(?:ro)?\.?\s*Nro\.?\s*:?\s*(\d{1,5})\s+(\d{1,8})", re.I)
_FECHA = re.compile(
    r"FECHA(?:\s+DE\s+EMISI[OÓ]N)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.I,
)
_FECHA_SOLA = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b")
_RAZON = re.compile(r"RAZ[OÓ]N\s+SOCIAL\s*:?[ \t]*(\S.*)", re.I)
_COPIA = re.compile(r"^\s*(?:ORIGINAL|DUPLICADO|TRIPLICADO)\s*$", re.I | re.M)
_ENTRECOMILLAS = re.compile(r"\"([^\"\n]{3,80})\"")
_CAE = re.compile(r"\bCAE\s*(?:N[°ºO.]*)?\s*:?\s*(\d{14})\b", re.I)
_CAE_ETIQUETA = re.compile(r"\bCAE\b", re.I)
_CAE_NUMERO = re.compile(r"\b(\d{14})\b")
_IMPORTE = r"([\d]{1,3}(?:\.\d{3})*,\d{2}|[\d]+[.,]\d{2}|[\d]+)"

# En el layout en columnas de AFIP, pypdf emite las etiquetas seguidas y los
# valores después, así que un "valor" puede ser en realidad la etiqueta siguiente.
_ETIQUETAS = (
    "domicilio",
    "condición",
    "condicion",
    "cuit",
    "ingresos brutos",
    "fecha",
    "período",
    "periodo",
    "apellido y nombre",
    "razón social",
    "razon social",
    "punto de venta",
    "comp",
    "código",
    "codigo",
    "importe",
    "subtotal",
)
_PALABRAS_ETIQUETA = sorted({e.split()[0] for e in _ETIQUETAS}, key=len, reverse=True)
_ETIQUETA_INTERCALADA = re.compile(
    r"\s+(?:" + "|".join(re.escape(p) for p in _PALABRAS_ETIQUETA) + r")\b[^:\n]{0,40}:",
    re.I,
)

# Sin \b inicial: pypdf suele pegarlo a lo anterior ("FACTURACCOD. 011").
_CODIGO_AFIP = re.compile(r"COD\.?\s*(\d{1,3})\b", re.I)
# Código de comprobante AFIP → letra. Incluye notas de crédito y débito de cada clase.
_POR_CODIGO = {
    1: TipoAfip.A,
    2: TipoAfip.A,
    3: TipoAfip.A,
    6: TipoAfip.B,
    7: TipoAfip.B,
    8: TipoAfip.B,
    11: TipoAfip.C,
    12: TipoAfip.C,
    13: TipoAfip.C,
}


def _solo_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


def parse_importe(texto: str) -> Decimal | None:
    bruto = texto.strip().replace(" ", "").replace("$", "")
    if not bruto:
        return None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{2}", bruto):
        bruto = bruto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+,\d{2}", bruto):
        bruto = bruto.replace(",", ".")
    elif re.fullmatch(r"\d+\.\d{2}", bruto):
        pass
    elif re.fullmatch(r"\d+", bruto):
        bruto = f"{bruto}.00"
    else:
        return None
    try:
        return Decimal(bruto)
    except InvalidOperation:
        return None


def _importe_etiqueta(texto: str, *etiquetas: str) -> Decimal | None:
    for etiqueta in etiquetas:
        # El "$" va entre la etiqueta y el número: "Importe Total: $ 63550,00".
        patron = re.compile(rf"{etiqueta}\s*:?\s*\$?\s*{_IMPORTE}", re.I)
        hallado = patron.search(texto)
        if hallado:
            valor = parse_importe(hallado.group(1))
            if valor is not None:
                return valor
        # Fallback: número antes de la etiqueta (hasta 400 chars atrás)
        patron_pos = re.compile(rf"{etiqueta}\s*:?\s*\$?", re.I)
        pos_matches = list(patron_pos.finditer(texto))
        if pos_matches:
            pos_match = pos_matches[-1]
            inicio = max(0, pos_match.start() - 400)
            fragmento = texto[inicio:pos_match.start()]
            nums = list(re.finditer(_IMPORTE, fragmento))
            for nm in reversed(nums):
                raw = nm.group(1)
                # Ignorar CUITs sueltos (11 dígitos sin separadores de importe)
                if re.fullmatch(r"\d{11}", raw):
                    continue
                # En fallback, descartar enteros planos sin decimales (pueden ser fechas/años)
                if re.fullmatch(r"\d+", raw):
                    continue
                valor = parse_importe(raw)
                if valor is not None:
                    return valor
    return None


def _total(texto: str) -> Decimal | None:
    valor = _importe_etiqueta(texto, r"IMPORTE\s+TOTAL", r"TOTAL")
    # Un total en cero siempre es un renglón mal leído ("Otros Tributos: $ 0,00"),
    # nunca el importe de la factura: mejor dejarlo vacío que cargar un dato falso.
    return valor or None


def _fecha(valor: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def _tipo_afip(texto: str) -> TipoAfip | None:
    letra = _FACTURA.search(texto)
    if letra:
        return TipoAfip(letra.group(1).upper())
    # En el recuadro de AFIP la letra suele salir suelta y el OCR la pierde,
    # pero el código de comprobante ("COD. 011") sobrevive y alcanza.
    codigo = _CODIGO_AFIP.search(texto)
    if codigo:
        return _POR_CODIGO.get(int(codigo.group(1)))
    return None


def _recortar_en_etiqueta(valor: str) -> str:
    # El OCR junta columnas vecinas en una línea: "ACME S.A. Fecha de Emisión: 11/09/2026".
    corte = _ETIQUETA_INTERCALADA.search(valor)
    return valor[: corte.start()].strip() if corte else valor.strip()


def _es_etiqueta(valor: str) -> bool:
    limpio = valor.strip().rstrip(":").strip()
    if not limpio or valor.strip().endswith(":"):
        return True
    bajo = limpio.lower()
    return any(bajo.startswith(e) for e in _ETIQUETAS)


def _razon_social(texto: str) -> str | None:
    candidatos: list[str] = []
    for match in _RAZON.finditer(texto):
        candidatos.append(match.group(1))
    # El nombre del emisor encabeza cada copia (ORIGINAL / DUPLICADO / TRIPLICADO).
    for match in _COPIA.finditer(texto):
        resto = texto[match.end() :].lstrip("\n")
        candidatos.append(resto.split("\n")[0])
    # Pie de la factura electrónica: el emisor va entre comillas.
    for match in _ENTRECOMILLAS.finditer(texto):
        candidatos.append(match.group(1))
    for bruto in candidatos:
        valor = _recortar_en_etiqueta(bruto.strip().split("\n")[0])
        if valor and not _es_etiqueta(valor):
            return valor
    return None


def _cae(texto: str) -> str | None:
    match = _CAE.search(texto)
    if match:
        return match.group(1)
    # Layout en columnas: la etiqueta "CAE N°:" queda lejos de su valor.
    etiqueta = _CAE_ETIQUETA.search(texto)
    if etiqueta:
        ventana = texto[etiqueta.end() : etiqueta.end() + 400]
        cercano = _CAE_NUMERO.search(ventana)
        if cercano:
            return cercano.group(1)
    return None


def _cuit_emisor(texto: str) -> str | None:
    bloque = texto
    receptor = re.search(r"(CUIT\s+(?:DEL\s+)?(?:COMPRADOR|RECEPTOR|CLIENTE).*)", texto, re.I | re.S)
    if receptor:
        bloque = texto[: receptor.start()]
    for match in _CUIT.finditer(bloque):
        d = _solo_digitos(match.group(1))
        if cuit_valido(d):
            return d
    for match in _CUIT.finditer(texto):
        d = _solo_digitos(match.group(1))
        if cuit_valido(d):
            return d
    return None


def parse_afip_text(texto: str) -> OcrResultado:
    if not (texto or "").strip():
        return OcrResultado()
    tipo = _tipo_afip(texto)
    pto = None
    nro = None
    m_comp = _COMP_NRO.search(texto)
    if m_comp:
        pto = int(m_comp.group(1))
        nro = int(m_comp.group(2))
    m_pvn = _PV_NRO.search(texto)
    if m_pvn and (pto is None or nro is None):
        if pto is None:
            pto = int(m_pvn.group(1))
        if nro is None:
            nro = int(m_pvn.group(2))
    m_pv = _PV.search(texto)
    if m_pv and pto is None:
        pto = int(m_pv.group(1))
    m_nro = _NRO.search(texto)
    if m_nro and nro is None:
        nro = int(m_nro.group(1))
    fecha = None
    m_fecha = _FECHA.search(texto) or _FECHA_SOLA.search(texto)
    if m_fecha:
        fecha = _fecha(m_fecha.group(1))
    return OcrResultado(
        cuit_emisor=_cuit_emisor(texto),
        razon_social=_razon_social(texto),
        tipo_afip=tipo,
        punto_venta=pto,
        numero=nro,
        fecha=fecha,
        neto_21=_importe_etiqueta(texto, r"NETO\s+GRAVADO(?:\s+21)?", r"IMPORTE\s+NETO\s+GRAVADO"),
        iva_21=_importe_etiqueta(texto, r"IVA\s*21\s*%"),
        neto_105=_importe_etiqueta(texto, r"NETO\s+GRAVADO\s*10[.,]5"),
        iva_105=_importe_etiqueta(texto, r"IVA\s*10[.,]5\s*%"),
        neto_27=_importe_etiqueta(texto, r"NETO\s+GRAVADO\s*27"),
        iva_27=_importe_etiqueta(texto, r"IVA\s*27\s*%"),
        no_gravado=_importe_etiqueta(texto, r"NO\s+GRAVADO", r"IMPORTE\s+NO\s+GRAVADO"),
        percep_iva=_importe_etiqueta(texto, r"PERCEP(?:CI[OÓ]N)?\.?\s*IVA"),
        percep_iibb=_importe_etiqueta(texto, r"PERCEP(?:CI[OÓ]N)?\.?\s*II?BB"),
        total=_total(texto),
        cae=_cae(texto),
    )
