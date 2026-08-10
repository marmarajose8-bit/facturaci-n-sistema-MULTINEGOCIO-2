import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Comercio
from core.security import decode_access_token

# HTTPBearer (en vez de OAuth2PasswordBearer) hace que el botón "Authorize" de
# Swagger muestre una sola casilla para pegar el token directo - más simple y
# confiable que el formulario de usuario/contraseña, que a veces no adjunta
# el header correctamente.
bearer_scheme = HTTPBearer()


def get_comercio_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Comercio:
    """
    Decodifica el JWT del header Authorization y devuelve el Comercio dueño de ese
    token. Este es el ÚNICO lugar de donde debe salir el comercio_id en los
    endpoints protegidos - nunca confiar en un comercio_id que mande el cliente.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credenciales.credentials
    try:
        payload = decode_access_token(token)
        comercio_id = payload.get("sub")
        if comercio_id is None:
            raise credenciales_invalidas
    except jwt.PyJWTError:
        raise credenciales_invalidas

    comercio = db.query(Comercio).filter(Comercio.id == int(comercio_id)).first()
    if not comercio:
        raise credenciales_invalidas
    if comercio.activo != "si":
        raise HTTPException(status_code=403, detail="Este comercio está suspendido")
    return comercio
