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
_RAZON = re.compile(r"RAZ[OÓ]N\s+SOCIAL\s*:?\s*(.+)", re.I)
_CAE = re.compile(r"\bCAE\s*(?:N[°ºO.]*)?\s*:?\s*(\d{14})\b", re.I)
_IMPORTE = r"([\d]{1,3}(?:\.\d{3})*,\d{2}|[\d]+[.,]\d{2}|[\d]+)"


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
        patron = re.compile(rf"{etiqueta}\s*:?\s*{_IMPORTE}", re.I)
        hallado = patron.search(texto)
        if hallado:
            valor = parse_importe(hallado.group(1))
            if valor is not None:
                return valor
        # Fallback: número antes de la etiqueta (hasta 400 chars atrás)
        patron_pos = re.compile(rf"{etiqueta}\s*:?", re.I)
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


def _fecha(valor: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
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
    tipo = None
    m_tipo = _FACTURA.search(texto)
    if m_tipo:
        tipo = TipoAfip(m_tipo.group(1).upper())
    if tipo is None:
        m_cod = re.search(r"FACTURA.*?COD\.?\s*0*(\d{2,3})\b", texto, re.I | re.S)
        if m_cod:
            codigo = m_cod.group(1)
            if codigo in ("001", "1"):
                tipo = TipoAfip.A
            elif codigo in ("006", "6"):
                tipo = TipoAfip.B
            elif codigo in ("011", "11"):
                tipo = TipoAfip.C
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
    razon = None
    m_razon = _RAZON.search(texto)
    if m_razon:
        razon = m_razon.group(1).strip().split("\n")[0].strip() or None
    cae = None
    m_cae = _CAE.search(texto)
    if m_cae:
        cae = m_cae.group(1)
    return OcrResultado(
        cuit_emisor=_cuit_emisor(texto),
        razon_social=razon,
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
        total=_importe_etiqueta(texto, r"IMPORTE\s+TOTAL", r"TOTAL"),
        cae=cae,
    )
