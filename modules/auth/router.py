from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Comercio
from core.security import verify_password, create_access_token
from core.cache import registrar_intento_fallido, bloqueado, limpiar_intentos, MAX_INTENTOS

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login del comercio. El campo 'username' del formulario es el RNC del comercio,
    'password' es la contraseña que se puso al registrarlo.

    Por seguridad, bloquea temporalmente los intentos después de varias
    contraseñas incorrectas seguidas para el mismo RNC (protege contra ataques
    de fuerza bruta). Si Redis no está disponible, esta protección se salta sin
    afectar el login normal.
    """
    if bloqueado(form.username):
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos fallidos para este RNC. Espera 15 minutos e intenta de nuevo.",
        )

    comercio = db.query(Comercio).filter(Comercio.rnc == form.username).first()
    if not comercio or not verify_password(form.password, comercio.password_hash):
        intentos = registrar_intento_fallido(form.username)
        restantes = max(0, MAX_INTENTOS - intentos)
        detalle = "RNC o contraseña incorrectos"
        if intentos > 0 and restantes > 0:
            detalle += f" ({restantes} intento(s) antes del bloqueo temporal)"
        elif intentos >= MAX_INTENTOS:
            detalle = "Demasiados intentos fallidos. Este RNC quedó bloqueado temporalmente por 15 minutos."
        raise HTTPException(status_code=401, detail=detalle)

    if comercio.activo != "si":
        raise HTTPException(status_code=403, detail="Este comercio está suspendido")

    limpiar_intentos(form.username)

    token = create_access_token(comercio_id=comercio.id, rnc=comercio.rnc)
    return {
        "access_token": token,
        "token_type": "bearer",
        "comercio_id": comercio.id,
        "nombre_comercial": comercio.nombre_comercial,
    }
