from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date

from core.database import get_db
from core.models import Empeno, Comercio

router = APIRouter(prefix="/prestamos", tags=["Préstamos Prendarios y Empeños - RYM"])


class ContratoEmpenoRYM(BaseModel):
    comercio_id: int
    cliente_nombre: str
    cedula_cliente: str
    bien_prendario: str  # Ej: "Pasola Honda Lead 125 - Chassis XXXXX"
    valor_tasacion: float
    monto_prestado: float
    tasa_interes_mensual: float = 2.0  # % mensual fijo adaptable
    fecha_inicio: date
    fecha_vencimiento_inamovible: date


def _validar_comercio(comercio_id: int, db: Session) -> Comercio:
    comercio = db.query(Comercio).filter(Comercio.id == comercio_id).first()
    if not comercio:
        raise HTTPException(status_code=404, detail=f"Comercio {comercio_id} no encontrado")
    return comercio


@router.post("/registrar-empeno-rym")
def registrar_empeno_rym(datos: ContratoEmpenoRYM, db: Session = Depends(get_db)):
    comercio = _validar_comercio(datos.comercio_id, db)

    interes_calculado = datos.monto_prestado * (datos.tasa_interes_mensual / 100)
    total_adeudado = datos.monto_prestado + interes_calculado

    empeno = Empeno(
        comercio_id=datos.comercio_id,
        cliente_nombre=datos.cliente_nombre,
        cedula_cliente=datos.cedula_cliente,
        bien_prendario=datos.bien_prendario,
        valor_tasacion=datos.valor_tasacion,
        monto_prestado=datos.monto_prestado,
        tasa_interes_mensual=datos.tasa_interes_mensual,
        interes_generado=round(interes_calculado, 2),
        total_a_pagar=round(total_adeudado, 2),
        fecha_inicio=datos.fecha_inicio,
        fecha_vencimiento_inamovible=datos.fecha_vencimiento_inamovible,
    )

    db.add(empeno)
    db.commit()
    db.refresh(empeno)

    return {
        "sistema": f"{comercio.nombre_comercial} - Préstamos Prendarios",
        "estado": empeno.estado,
        "id": empeno.id,
        "comercio_id": empeno.comercio_id,
        "cliente": empeno.cliente_nombre,
        "cedula": empeno.cedula_cliente,
        "garantia": empeno.bien_prendario,
        "tasacion": empeno.valor_tasacion,
        "capital_prestado": empeno.monto_prestado,
        "interes_generado": empeno.interes_generado,
        "total_a_pagar": empeno.total_a_pagar,
        "vencimiento": empeno.fecha_vencimiento_inamovible,
    }


@router.get("/empenos")
def listar_empenos(comercio_id: int, db: Session = Depends(get_db)):
    _validar_comercio(comercio_id, db)
    empenos = (
        db.query(Empeno)
        .filter(Empeno.comercio_id == comercio_id)
        .order_by(Empeno.id.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "cliente": e.cliente_nombre,
            "garantia": e.bien_prendario,
            "total_a_pagar": e.total_a_pagar,
            "vencimiento": e.fecha_vencimiento_inamovible,
            "estado": e.estado,
        }
        for e in empenos
    ]


@router.get("/empenos/{empeno_id}")
def obtener_empeno(empeno_id: int, comercio_id: int, db: Session = Depends(get_db)):
    empeno = (
        db.query(Empeno)
        .filter(Empeno.id == empeno_id, Empeno.comercio_id == comercio_id)
        .first()
    )
    if not empeno:
        raise HTTPException(status_code=404, detail="Empeño no encontrado")

    return {
        "id": empeno.id,
        "comercio_id": empeno.comercio_id,
        "cliente": empeno.cliente_nombre,
        "cedula": empeno.cedula_cliente,
        "garantia": empeno.bien_prendario,
        "tasacion": empeno.valor_tasacion,
        "capital_prestado": empeno.monto_prestado,
        "tasa_interes_mensual": empeno.tasa_interes_mensual,
        "interes_generado": empeno.interes_generado,
        "total_a_pagar": empeno.total_a_pagar,
        "fecha_inicio": empeno.fecha_inicio,
        "vencimiento": empeno.fecha_vencimiento_inamovible,
        "estado": empeno.estado,
    }
