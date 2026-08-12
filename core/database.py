import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# En Railway, la variable DATABASE_URL la inyecta automáticamente el plugin de
# PostgreSQL. En local (Chromebook), si no existe esa variable, usamos SQLite
# como hasta ahora - así no hace falta instalar Postgres para seguir probando.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway a veces entrega la URL con el prefijo viejo "postgres://", pero
    # SQLAlchemy moderno exige "postgresql://" - lo normalizamos por si acaso.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./rym_multinegocio.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
