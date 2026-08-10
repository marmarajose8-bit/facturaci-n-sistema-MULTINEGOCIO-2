from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Comercio
from core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login del comercio. El campo 'username' del formulario es el RNC del comercio,
    'password' es la contraseña que se puso al registrarlo.
    """
    comercio = db.query(Comercio).filter(Comercio.rnc == form.username).first()
    if not comercio or not verify_password(form.password, comercio.password_hash):
        raise HTTPException(status_code=401, detail="RNC o contraseña incorrectos")
    if comercio.activo != "si":
        raise HTTPException(status_code=403, detail="Este comercio está suspendido")

    token = create_access_token(comercio_id=comercio.id, rnc=comercio.rnc)
    return {
        "access_token": token,
        "token_type": "bearer",
        "comercio_id": comercio.id,
        "nombre_comercial": comercio.nombre_comercial,
    }
