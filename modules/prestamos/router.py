from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/prestamos", tags=["Préstamos Prendarios y Empeños - RYM"])

class ContratoEmpenoRYM(BaseModel):
    cliente_nombre: str
    cedula_cliente: str
    bien_prendario: str  # Ej: "Pasola Honda Lead 125 - Chassis XXXXX"
    valor_tasacion: float
    monto_prestado: float
    tasa_interes_mensual: float = 2.0  # % mensual fijo adaptable
    fecha_inicio: date
    fecha_vencimiento_inamovible: date

@router.post("/registrar-empeno-rym")
def registrar_empeno_rym(datos: ContratoEmpenoRYM):
    interes_calculado = datos.monto_prestado * (datos.tasa_interes_mensual / 100)
    total_adeudado = datos.monto_prestado + interes_calculado
    
    return {
        "sistema": "RYM Inversiones - Préstamos Prendarios",
        "estado": "Contrato Activo",
        "cliente": datos.cliente_nombre,
        "cedula": datos.cedula_cliente,
        "garantia": datos.bien_prendario,
        "tasacion": datos.valor_tasacion,
        "capital_prestado": datos.monto_prestado,
        "interes_generado": interes_calculado,
        "total_a_pagar": total_adeudado,
        "vencimiento": datos.fecha_vencimiento_inamovible
    }
