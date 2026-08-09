from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.settings import MONEDA
from core.database import get_db
from core.models import Dominio, Comercio

router = APIRouter(prefix="/dominios", tags=["Reventa de Dominios y Web - RD"])


class SolicitudDominio(BaseModel):
    comercio_id: int
    dominio: str
    extension: str  # Ej: ".com", ".do", ".com.do"
    cliente: str
    contacto_correo: str


def _validar_comercio(comercio_id: int, db: Session) -> Comercio:
    comercio = db.query(Comercio).filter(Comercio.id == comercio_id).first()
    if not comercio:
        raise HTTPException(status_code=404, detail=f"Comercio {comercio_id} no encontrado")
    return comercio


@router.post("/consultar-y-registrar")
def consultar_y_registrar(datos: SolicitudDominio, db: Session = Depends(get_db)):
    comercio = _validar_comercio(datos.comercio_id, db)

    nombre_completo = f"{datos.dominio}{datos.extension}"

    # Simulación de cotización adaptada al mercado local (RD)
    # TODO: reemplazar por una llamada real a un registrador mayorista (ej. httpx + API de ResellerClub / NIC.do)
    precio_base_dop = 1200.0 if datos.extension == ".do" else 950.0

    registro = Dominio(
        comercio_id=datos.comercio_id,
        dominio=datos.dominio,
        extension=datos.extension,
        nombre_completo=nombre_completo,
        cliente=datos.cliente,
        contacto_correo=datos.contacto_correo,
        precio_anual=precio_base_dop,
    )

    db.add(registro)
    db.commit()
    db.refresh(registro)

    return {
        "entidad": comercio.nombre_comercial,
        "modulo": "Reventa de Dominios",
        "estado": "Dominio Registrado con Exito",
        "comercio_id": registro.comercio_id,
        "dominio": registro.nombre_completo,
        "cliente": registro.cliente,
        "correo": registro.contacto_correo,
        "precio_anual": registro.precio_anual,
        "moneda": MONEDA,
        "aviso": "Sujeto a disponibilidad en registro oficial NIC.do / ICANN",
    }


@router.get("/dominios")
def listar_dominios(comercio_id: int, db: Session = Depends(get_db)):
    _validar_comercio(comercio_id, db)
    dominios = (
        db.query(Dominio)
        .filter(Dominio.comercio_id == comercio_id)
        .order_by(Dominio.id.desc())
        .all()
    )
    return [
        {
            "dominio": d.nombre_completo,
            "cliente": d.cliente,
            "precio_anual": d.precio_anual,
            "fecha_registro": d.fecha_registro,
        }
        for d in dominios
    ]
