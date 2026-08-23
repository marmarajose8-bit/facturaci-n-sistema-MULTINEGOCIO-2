import os
import redis

REDIS_URL = os.getenv("REDIS_URL")

_cliente = None
if REDIS_URL:
    try:
        _cliente = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        _cliente.ping()
    except Exception:
        _cliente = None  # si Redis no responde, seguimos sin bloqueo de intentos - no rompe el login


def redis_disponible() -> bool:
    return _cliente is not None


MAX_INTENTOS = 5
VENTANA_SEGUNDOS = 15 * 60  # 15 minutos


def registrar_intento_fallido(rnc: str) -> int:
    """Suma un intento fallido para este RNC y devuelve el total acumulado en la ventana actual."""
    if not _cliente:
        return 0
    clave = f"login_intentos:{rnc}"
    try:
        total = _cliente.incr(clave)
        if total == 1:
            _cliente.expire(clave, VENTANA_SEGUNDOS)
        return total
    except Exception:
        return 0


def intentos_restantes(rnc: str) -> int:
    if not _cliente:
        return MAX_INTENTOS
    try:
        actual = _cliente.get(f"login_intentos:{rnc}")
        actual = int(actual) if actual else 0
        return max(0, MAX_INTENTOS - actual)
    except Exception:
        return MAX_INTENTOS


def bloqueado(rnc: str) -> bool:
    if not _cliente:
        return False
    try:
        actual = _cliente.get(f"login_intentos:{rnc}")
        return int(actual) >= MAX_INTENTOS if actual else False
    except Exception:
        return False


def limpiar_intentos(rnc: str):
    """Se llama cuando el login es exitoso - resetea el contador."""
    if not _cliente:
        return
    try:
        _cliente.delete(f"login_intentos:{rnc}")
    except Exception:
        pass
