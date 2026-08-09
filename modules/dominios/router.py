from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/dominios", tags=["Revventa de Dominios y Web"])

class ConsultaDominio(BaseModel):
    dominio: str  # Ej: "tutienda.com"

@router.post("/verificar-disponibilidad")
def verificar_disponibilidad(datos: ConsultaDominio):
    # Lógica de integración futura con API de mayorista (Namecheap/Reseller)
    return {
        "estado": "consultado",
        "dominio": datos.dominio,
        "disponible": True,
        "precio_sugerido_venta": 15.00,  # Incluyendo tu margen de ganancia
        "moneda": "USD"
    }
