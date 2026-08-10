from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import date

from core.database import get_db
from core.models import Comercio, SecuenciaNCF
from core.security import hash_password
from core.deps import get_comercio_actual

router = APIRouter(prefix="/comercios", tags=["Comercios (Tenants)"])


class RegistroComercio(BaseModel):
    nombre_comercial: str
    rnc: str
    email_contacto: EmailStr
    password: str
    plan: str = "basico"


@router.post("/registrar")
def registrar_comercio(datos: RegistroComercio, db: Session = Depends(get_db)):
    existente = db.query(Comercio).filter(Comercio.rnc == datos.rnc).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un comercio registrado con el RNC {datos.rnc}",
        )
    if len(datos.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    comercio = Comercio(
        nombre_comercial=datos.nombre_comercial,
        rnc=datos.rnc,
        email_contacto=datos.email_contacto,
        password_hash=hash_password(datos.password),
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
        "aviso": "Inicia sesión en POST /auth/login con tu RNC y contraseña para obtener tu token de acceso.",
    }


# ---------- Endpoints propios (requieren sesión) ----------

@router.get("/yo")
def mi_comercio(comercio_actual: Comercio = Depends(get_comercio_actual)):
    return {
        "id": comercio_actual.id,
        "nombre_comercial": comercio_actual.nombre_comercial,
        "rnc": comercio_actual.rnc,
        "email_contacto": comercio_actual.email_contacto,
        "plan": comercio_actual.plan,
        "activo": comercio_actual.activo,
        "fecha_creacion": comercio_actual.fecha_creacion,
    }


# ---------- Secuencias NCF (DGII) - requieren sesión del propio comercio ----------

class RegistroSecuenciaNCF(BaseModel):
    tipo_ncf: str  # Ej: "B02" (Consumo), "B01" (Crédito Fiscal)
    descripcion: str | None = None
    secuencia_desde: int
    secuencia_hasta: int
    fecha_vencimiento: date


@router.post("/secuencias-ncf")
def registrar_secuencia_ncf(
    datos: RegistroSecuenciaNCF,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    """
    Registra el rango de NCF que la DGII autorizó a ESTE comercio (el dueño del
    token) para un tipo de comprobante. Esto viene de la Autorización de Impresión
    / Secuencia que la DGII le entrega al negocio - aquí solo se transcribe.
    """
    if datos.secuencia_desde > datos.secuencia_hasta:
        raise HTTPException(status_code=400, detail="secuencia_desde no puede ser mayor que secuencia_hasta")

    existente = (
        db.query(SecuenciaNCF)
        .filter(SecuenciaNCF.comercio_id == comercio_actual.id, SecuenciaNCF.tipo_ncf == datos.tipo_ncf)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya tienes una secuencia registrada para el tipo {datos.tipo_ncf}. "
                   f"Si la DGII te autorizó un rango nuevo, hay que dar de baja la anterior primero.",
        )

    secuencia = SecuenciaNCF(
        comercio_id=comercio_actual.id,
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
        "tipo_ncf": secuencia.tipo_ncf,
        "rango": f"{secuencia.tipo_ncf}{secuencia.secuencia_desde:08d} - {secuencia.tipo_ncf}{secuencia.secuencia_hasta:08d}",
        "fecha_vencimiento": secuencia.fecha_vencimiento,
    }


@router.get("/secuencias-ncf")
def listar_secuencias_ncf(
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    secuencias = db.query(SecuenciaNCF).filter(SecuenciaNCF.comercio_id == comercio_actual.id).all()
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
