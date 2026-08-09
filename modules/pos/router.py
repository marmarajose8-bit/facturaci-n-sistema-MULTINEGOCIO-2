from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from config.settings import MONEDA, ITBIS_GENERAL, EMPRESA
from core.database import get_db
from core.models import Factura, DetalleFactura

router = APIRouter(prefix="/pos", tags=["POS y Facturación - RD"])


class DetalleItem(BaseModel):
    descripcion: str
    cantidad: int
    precio_unitario: float


class FacturaRD(BaseModel):
    nro_factura: str
    cliente: str
    rnc_cedula: str
    items: List[DetalleItem]
    metodo_pago: str  # Efectivo, Transferencia, Tarjeta


@router.post("/emitir-factura-rd")
def emitir_factura_rd(datos: FacturaRD, db: Session = Depends(get_db)):
    existente = db.query(Factura).filter(Factura.nro_factura == datos.nro_factura).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una factura con el número {datos.nro_factura}",
        )

    subtotal = sum(item.cantidad * item.precio_unitario for item in datos.items)
    itbis = subtotal * ITBIS_GENERAL
    total_con_itbis = subtotal + itbis

    factura = Factura(
        nro_factura=datos.nro_factura,
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
        "entidad": EMPRESA,
        "estado": "Factura Fiscal Generada",
        "factura": factura.nro_factura,
        "cliente": factura.cliente,
        "rnc_cedula": factura.rnc_cedula,
        "subtotal": factura.subtotal,
        "itbis_18": factura.itbis,
        "total_pagar": factura.total_pagar,
        "moneda": MONEDA,
        "metodo_pago": factura.metodo_pago,
    }


@router.get("/facturas")
def listar_facturas(db: Session = Depends(get_db)):
    facturas = db.query(Factura).order_by(Factura.id.desc()).all()
    return [
        {
            "factura": f.nro_factura,
            "cliente": f.cliente,
            "total_pagar": f.total_pagar,
            "metodo_pago": f.metodo_pago,
            "fecha_emision": f.fecha_emision,
        }
        for f in facturas
    ]


@router.get("/facturas/{nro_factura}")
def obtener_factura(nro_factura: str, db: Session = Depends(get_db)):
    factura = db.query(Factura).filter(Factura.nro_factura == nro_factura).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    return {
        "entidad": EMPRESA,
        "factura": factura.nro_factura,
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
