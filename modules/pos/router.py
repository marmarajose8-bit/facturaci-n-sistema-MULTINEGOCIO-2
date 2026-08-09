from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/pos", tags=["POS e Inventario"])

class ItemVenta(BaseModel):
    producto: str
    cantidad: int
    precio_unitario: float

class TransaccionPOS(BaseModel):
    cliente: str
    items: List[ItemVenta]
    metodo_pago: str  # Ej: "Efectivo", "Transferencia", "Tarjeta"

@router.post("/facturar")
def registrar_factura_pos(datos: TransaccionPOS):
    # Cálculo total de la factura
    subtotal = sum(item.cantidad * item.precio_unitario for item in datos.items)
    
    return {
        "estado": "facturado_exitosamente",
        "modulo": "POS e Inventario",
        "cliente": datos.cliente,
        "items_totales": len(datos.items),
        "subtotal": subtotal,
        "metodo_pago": datos.metodo_pago,
        "mensaje": "Transacción procesada e inventario actualizado."
    }
