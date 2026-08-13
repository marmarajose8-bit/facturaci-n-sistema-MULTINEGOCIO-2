import os
from fastapi import FastAPI

from core.database import Base, engine
from core import models  # noqa: F401 - registra los modelos en Base antes de crear las tablas
from modules.auth.router import router as auth_router
from modules.comercios.router import router as comercios_router
from modules.prestamos.router import router as prestamos_router
from modules.dominios.router import router as dominios_router
from modules.pos.router import router as pos_router

# Crea las tablas en la base de datos si todavía no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JG Facturaciones",
    version="1.0.0",
    description="Plataforma modular centralizada con POS, Préstamos Prendarios y Reventa de Dominios."
)

# Incluir los routers de los módulos del ecosistema
app.include_router(auth_router)
app.include_router(comercios_router)
app.include_router(prestamos_router)
app.include_router(dominios_router)
app.include_router(pos_router)

@app.get("/")
def read_root():
    return {
        "estado": "activo",
        "sistema": "JG Facturaciones",
        "modulos": ["Autenticación", "Comercios", "POS e Inventario", "Préstamos y Empeños", "Dominios y Web"],
        "base_de_datos": engine.dialect.name,  # "postgresql" si está bien conectado, "sqlite" si NO
        "database_url_detectada": bool(os.getenv("DATABASE_URL")),
    }
