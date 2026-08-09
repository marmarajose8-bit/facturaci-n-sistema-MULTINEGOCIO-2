from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from config.settings import MONEDA, ITBIS_GENERAL, EMPRESA

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
def emitir_factura_rd(datos: FacturaRD):
    subtotal = sum(item.cantidad * item.precio_unitario for item in datos.items)
    itbis = subtotal * ITBIS_GENERAL
    total_con_itbis = subtotal + itbis
    
    return {
        "entidad": EMPRESA,
        "estado": "Factura Fiscal Generada",
        "factura": datos.nro_factura,
        "cliente": datos.cliente,
        "rnc_cedula": datos.rnc_cedula,
        "subtotal": round(subtotal, 2),
        "itbis_18": round(itbis, 2),
        "total_pagar": round(total_con_itbis, 2),
        "moneda": MONEDA,
        "metodo_pago": datos.metodo_pago
    }
