from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/prestamos", tags=["Préstamos Prendarios y Empeños"])

class PrestamoPrendario(BaseModel):
    cliente: str
    activo_prendario: str  # Ej: "Pasola Honda Lead", "Motor CG"
    valor_tasacion: float
    monto_prestamo: float
    porcentaje_interes: float  # Ej: 1.0 para el 1% estricto
    fecha_vencimiento: date   # Inamovible

@router.post("/crear-empeno")
def crear_empeno(datos: PrestamoPrendario):
    interes_calculado = datos.monto_prestamo * (datos.porcentaje_interes / 100)
    total_a_pagar = datos.monto_prestamo + interes_calculado
    
    return {
        "estado": "registrado_exitosamente",
        "tipo": "Préstamo Prendario / Empeño",
        "cliente": datos.cliente,
        "activo": datos.activo_prendario,
        "capital": datos.monto_prestamo,
        "interes_porcentual": f"{datos.porcentaje_interes}%",
        "monto_interes": interes_calculado,
        "total_general": total_a_pagar,
        "fecha_vencimiento_inamovible": datos.fecha_vencimiento
    }
