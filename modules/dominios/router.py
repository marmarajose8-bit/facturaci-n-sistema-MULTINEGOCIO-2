from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config.settings import MONEDA, EMPRESA

router = APIRouter(prefix="/dominios", tags=["Reventa de Dominios y Web - RD"])

class SolicitudDominio(BaseModel):
    dominio: str
    extension: str  # Ej: ".com", ".do", ".com.do"
    cliente: str
    contacto_correo: str

@router.post("/consultar-y-registrar")
def consultar_y_registrar(datos: SolicitudDominio):
    nombre_completo = f"{datos.dominio}{datos.extension}"
    
    # Simulación de cotización adaptada al mercado local (RD)
    precio_base_dop = 1200.0 if datos.extension == ".do" else 950.0
    
    return {
        "entidad": EMPRESA,
        "modulo": "Reventa de Dominios",
        "estado": "Dominio Registrado con Exito",
        "dominio": nombre_completo,
        "cliente": datos.cliente,
        "correo": datos.contacto_correo,
        "precio_anual": precio_base_dop,
        "moneda": MONEDA,
        "aviso": "Sujeto a disponibilidad en registro oficial NIC.do / ICANN"
    }
