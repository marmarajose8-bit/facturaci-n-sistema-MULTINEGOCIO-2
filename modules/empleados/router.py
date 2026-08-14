from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from core.database import get_db
from core.models import Empleado, Comercio
from core.deps import get_comercio_actual
from core.security import hash_password, verify_password

router = APIRouter(prefix="/comercios/empleados", tags=["Empleados (Cajeros)"])


class RegistroEmpleado(BaseModel):
    nombre: str
    pin: str
    rol: str = "cajero"  # "cajero" o "admin"

    @field_validator("pin")
    @classmethod
    def pin_valido(cls, v):
        if not v.isdigit() or not (4 <= len(v) <= 6):
            raise ValueError("El PIN debe tener entre 4 y 6 dígitos numéricos")
        return v


@router.post("")
def registrar_empleado(
    datos: RegistroEmpleado,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    # Revisamos que ningún empleado activo de este comercio use ya ese PIN,
    # comparando contra el hash (no se puede indexar en la DB porque el hash
    # de bcrypt siempre es distinto aunque el PIN sea igual).
    activos = (
        db.query(Empleado)
        .filter(Empleado.comercio_id == comercio_actual.id, Empleado.activo == "si")
        .all()
    )
    for e in activos:
        if verify_password(datos.pin, e.pin_hash):
            raise HTTPException(status_code=400, detail="Ese PIN ya está en uso por otro empleado activo")

    empleado = Empleado(
        comercio_id=comercio_actual.id,
        nombre=datos.nombre,
        pin_hash=hash_password(datos.pin),
        rol=datos.rol,
    )
    db.add(empleado)
    db.commit()
    db.refresh(empleado)

    return {
        "estado": "Empleado Registrado",
        "id": empleado.id,
        "nombre": empleado.nombre,
        "rol": empleado.rol,
    }


@router.get("")
def listar_empleados(
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    empleados = db.query(Empleado).filter(Empleado.comercio_id == comercio_actual.id).all()
    return [
        {"id": e.id, "nombre": e.nombre, "rol": e.rol, "activo": e.activo}
        for e in empleados
    ]


@router.delete("/{empleado_id}")
def desactivar_empleado(
    empleado_id: int,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    empleado = (
        db.query(Empleado)
        .filter(Empleado.id == empleado_id, Empleado.comercio_id == comercio_actual.id)
        .first()
    )
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    empleado.activo = "no"
    db.add(empleado)
    db.commit()

    return {"estado": "Empleado Desactivado", "id": empleado.id, "nombre": empleado.nombre}
