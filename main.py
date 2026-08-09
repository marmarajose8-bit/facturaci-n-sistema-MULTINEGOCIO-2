from fastapi import FastAPI
from modules.prestamos.router import router as prestamos_router
from modules.dominios.router import router as dominios_router
from modules.pos.router import router as pos_router

app = FastAPI(
    title="Ecosistema SaaS Multinegocio RYM",
    version="1.0.0",
    description="Plataforma modular centralizada con POS, Préstamos Prendarios y Reventa de Dominios."
)

# Incluir los routers de los módulos del ecosistema
app.include_router(prestamos_router)
app.include_router(dominios_router)
app.include_router(pos_router)

@app.get("/")
def read_root():
    return {
        "estado": "activo",
        "sistema": "SaaS Multinegocio RYM",
        "modulos": ["POS e Inventario", "Préstamos y Empeños", "Dominios y Web"]
    }
