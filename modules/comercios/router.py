from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import date

from core.database import get_db
from core.models import Comercio, SecuenciaNCF

router = APIRouter(prefix="/comercios", tags=["Comercios (Tenants)"])


class RegistroComercio(BaseModel):
    nombre_comercial: str
    rnc: str
    email_contacto: EmailStr
    plan: str = "basico"


def _validar_comercio(comercio_id: int, db: Session) -> Comercio:
    comercio = db.query(Comercio).filter(Comercio.id == comercio_id).first()
    if not comercio:
        raise HTTPException(status_code=404, detail=f"Comercio {comercio_id} no encontrado")
    return comercio


@router.post("/registrar")
def registrar_comercio(datos: RegistroComercio, db: Session = Depends(get_db)):
    existente = db.query(Comercio).filter(Comercio.rnc == datos.rnc).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un comercio registrado con el RNC {datos.rnc}",
        )

    comercio = Comercio(
        nombre_comercial=datos.nombre_comercial,
        rnc=datos.rnc,
        email_contacto=datos.email_contacto,
        plan=datos.plan,
    )
    db.add(comercio)
    db.commit()
    db.refresh(comercio)

    return {
        "estado": "Comercio Registrado",
        "id": comercio.id,
        "nombre_comercial": comercio.nombre_comercial,
        "rnc": comercio.rnc,
        "plan": comercio.plan,
    }


@router.get("")
def listar_comercios(db: Session = Depends(get_db)):
    comercios = db.query(Comercio).order_by(Comercio.id.desc()).all()
    return [
        {
            "id": c.id,
            "nombre_comercial": c.nombre_comercial,
            "rnc": c.rnc,
            "plan": c.plan,
            "activo": c.activo,
        }
        for c in comercios
    ]


@router.get("/{comercio_id}")
def obtener_comercio(comercio_id: int, db: Session = Depends(get_db)):
    comercio = _validar_comercio(comercio_id, db)
    return {
        "id": comercio.id,
        "nombre_comercial": comercio.nombre_comercial,
        "rnc": comercio.rnc,
        "email_contacto": comercio.email_contacto,
        "plan": comercio.plan,
        "activo": comercio.activo,
        "fecha_creacion": comercio.fecha_creacion,
    }


# ---------- Secuencias NCF (DGII) ----------

class RegistroSecuenciaNCF(BaseModel):
    tipo_ncf: str  # Ej: "B02" (Consumo), "B01" (Crédito Fiscal)
    descripcion: str | None = None
    secuencia_desde: int
    secuencia_hasta: int
    fecha_vencimiento: date


@router.post("/{comercio_id}/secuencias-ncf")
def registrar_secuencia_ncf(comercio_id: int, datos: RegistroSecuenciaNCF, db: Session = Depends(get_db)):
    """
    Registra el rango de NCF que la DGII autorizó a este comercio para un tipo de
    comprobante. Esto viene de la Autorización de Impresión / Secuencia que la DGII
    le entrega al negocio - aquí solo se transcribe, no se inventa.
    """
    _validar_comercio(comercio_id, db)

    if datos.secuencia_desde > datos.secuencia_hasta:
        raise HTTPException(status_code=400, detail="secuencia_desde no puede ser mayor que secuencia_hasta")

    existente = (
        db.query(SecuenciaNCF)
        .filter(SecuenciaNCF.comercio_id == comercio_id, SecuenciaNCF.tipo_ncf == datos.tipo_ncf)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Este comercio ya tiene una secuencia registrada para el tipo {datos.tipo_ncf}. "
                   f"Si la DGII le autorizó un rango nuevo, hay que dar de baja la anterior primero.",
        )

    secuencia = SecuenciaNCF(
        comercio_id=comercio_id,
        tipo_ncf=datos.tipo_ncf,
        descripcion=datos.descripcion,
        secuencia_desde=datos.secuencia_desde,
        secuencia_hasta=datos.secuencia_hasta,
        secuencia_actual=datos.secuencia_desde,
        fecha_vencimiento=datos.fecha_vencimiento,
    )
    db.add(secuencia)
    db.commit()
    db.refresh(secuencia)

    return {
        "estado": "Secuencia NCF Registrada",
        "id": secuencia.id,
        "comercio_id": comercio_id,
        "tipo_ncf": secuencia.tipo_ncf,
        "rango": f"{secuencia.tipo_ncf}{secuencia.secuencia_desde:08d} - {secuencia.tipo_ncf}{secuencia.secuencia_hasta:08d}",
        "fecha_vencimiento": secuencia.fecha_vencimiento,
    }


@router.get("/{comercio_id}/secuencias-ncf")
def listar_secuencias_ncf(comercio_id: int, db: Session = Depends(get_db)):
    _validar_comercio(comercio_id, db)
    secuencias = db.query(SecuenciaNCF).filter(SecuenciaNCF.comercio_id == comercio_id).all()
    return [
        {
            "tipo_ncf": s.tipo_ncf,
            "descripcion": s.descripcion,
            "proximo_ncf": f"{s.tipo_ncf}{s.secuencia_actual:08d}",
            "disponibles": s.secuencia_hasta - s.secuencia_actual + 1,
            "fecha_vencimiento": s.fecha_vencimiento,
            "activa": s.activa,
        }
        for s in secuencias
    ]
