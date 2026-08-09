from datetime import date

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from config.settings import MONEDA, ITBIS_GENERAL
from core.database import get_db
from core.models import Factura, DetalleFactura, Comercio, SecuenciaNCF

router = APIRouter(prefix="/pos", tags=["POS y Facturación - RD"])


class DetalleItem(BaseModel):
    descripcion: str
    cantidad: int
    precio_unitario: float


class FacturaRD(BaseModel):
    comercio_id: int
    tipo_ncf: str  # Ej: "B02" (Consumo), "B01" (Crédito Fiscal) - el NCF lo genera el sistema
    cliente: str
    rnc_cedula: str
    items: List[DetalleItem]
    metodo_pago: str  # Efectivo, Transferencia, Tarjeta


def _validar_comercio(comercio_id: int, db: Session) -> Comercio:
    comercio = db.query(Comercio).filter(Comercio.id == comercio_id).first()
    if not comercio:
        raise HTTPException(status_code=404, detail=f"Comercio {comercio_id} no encontrado")
    return comercio


def _siguiente_ncf(comercio_id: int, tipo_ncf: str, db: Session) -> str:
    """
    Toma el próximo número disponible de la secuencia NCF autorizada por la DGII
    para este comercio y tipo de comprobante, valida rango y vencimiento, y avanza
    el contador. Esto es lo que hace que el número de factura sea fiscalmente válido.
    """
    secuencia = (
        db.query(SecuenciaNCF)
        .filter(SecuenciaNCF.comercio_id == comercio_id, SecuenciaNCF.tipo_ncf == tipo_ncf)
        .first()
    )
    if not secuencia:
        raise HTTPException(
            status_code=400,
            detail=f"Este comercio no tiene una secuencia NCF autorizada para el tipo '{tipo_ncf}'. "
                   f"Regístrala primero en POST /comercios/{{comercio_id}}/secuencias-ncf",
        )
    if secuencia.activa != "si":
        raise HTTPException(status_code=400, detail=f"La secuencia NCF '{tipo_ncf}' de este comercio está inactiva")
    if secuencia.fecha_vencimiento < date.today():
        raise HTTPException(
            status_code=400,
            detail=f"La secuencia NCF '{tipo_ncf}' venció el {secuencia.fecha_vencimiento}. "
                   f"Hay que solicitar una nueva autorización a la DGII.",
        )
    if secuencia.secuencia_actual > secuencia.secuencia_hasta:
        raise HTTPException(
            status_code=400,
            detail=f"La secuencia NCF '{tipo_ncf}' de este comercio se agotó. "
                   f"Hay que solicitar un nuevo rango a la DGII.",
        )

    ncf = f"{tipo_ncf}{secuencia.secuencia_actual:08d}"
    secuencia.secuencia_actual += 1
    db.add(secuencia)
    return ncf


@router.post("/emitir-factura-rd")
def emitir_factura_rd(datos: FacturaRD, db: Session = Depends(get_db)):
    comercio = _validar_comercio(datos.comercio_id, db)
    ncf_generado = _siguiente_ncf(datos.comercio_id, datos.tipo_ncf, db)

    subtotal = sum(item.cantidad * item.precio_unitario for item in datos.items)
    itbis = subtotal * ITBIS_GENERAL
    total_con_itbis = subtotal + itbis

    factura = Factura(
        comercio_id=datos.comercio_id,
        nro_factura=ncf_generado,
        tipo_ncf=datos.tipo_ncf,
        cliente=datos.cliente,
        rnc_cedula=datos.rnc_cedula,
        subtotal=round(subtotal, 2),
        itbis=round(itbis, 2),
        total_pagar=round(total_con_itbis, 2),
        metodo_pago=datos.metodo_pago,
    )
    factura.items = [
        DetalleFactura(
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
        )
        for item in datos.items
    ]

    db.add(factura)
    db.commit()
    db.refresh(factura)

    return {
        "entidad": comercio.nombre_comercial,
        "estado": "Factura Fiscal Generada",
        "comercio_id": factura.comercio_id,
        "ncf": factura.nro_factura,
        "tipo_ncf": factura.tipo_ncf,
        "cliente": factura.cliente,
        "rnc_cedula": factura.rnc_cedula,
        "subtotal": factura.subtotal,
        "itbis_18": factura.itbis,
        "total_pagar": factura.total_pagar,
        "moneda": MONEDA,
        "metodo_pago": factura.metodo_pago,
    }


@router.get("/facturas")
def listar_facturas(comercio_id: int, db: Session = Depends(get_db)):
    """Lista las facturas de UN comercio. comercio_id es obligatorio para no mezclar tenants."""
    _validar_comercio(comercio_id, db)
    facturas = (
        db.query(Factura)
        .filter(Factura.comercio_id == comercio_id)
        .order_by(Factura.id.desc())
        .all()
    )
    return [
        {
            "ncf": f.nro_factura,
            "tipo_ncf": f.tipo_ncf,
            "cliente": f.cliente,
            "total_pagar": f.total_pagar,
            "metodo_pago": f.metodo_pago,
            "fecha_emision": f.fecha_emision,
        }
        for f in facturas
    ]


@router.get("/facturas/{ncf}")
def obtener_factura(ncf: str, comercio_id: int, db: Session = Depends(get_db)):
    factura = (
        db.query(Factura)
        .filter(Factura.comercio_id == comercio_id, Factura.nro_factura == ncf)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    return {
        "entidad": factura.comercio.nombre_comercial,
        "comercio_id": factura.comercio_id,
        "ncf": factura.nro_factura,
        "tipo_ncf": factura.tipo_ncf,
        "cliente": factura.cliente,
        "rnc_cedula": factura.rnc_cedula,
        "subtotal": factura.subtotal,
        "itbis_18": factura.itbis,
        "total_pagar": factura.total_pagar,
        "moneda": MONEDA,
        "metodo_pago": factura.metodo_pago,
        "items": [
            {
                "descripcion": item.descripcion,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
            }
            for item in factura.items
        ],
    }
