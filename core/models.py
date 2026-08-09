from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from core.database import Base


class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    nro_factura = Column(String, unique=True, index=True, nullable=False)
    cliente = Column(String, nullable=False)
    rnc_cedula = Column(String, nullable=False)
    subtotal = Column(Float, nullable=False)
    itbis = Column(Float, nullable=False)
    total_pagar = Column(Float, nullable=False)
    metodo_pago = Column(String, nullable=False)
    fecha_emision = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "DetalleFactura", back_populates="factura", cascade="all, delete-orphan"
    )


class DetalleFactura(Base):
    __tablename__ = "detalle_facturas"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False)
    descripcion = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)

    factura = relationship("Factura", back_populates="items")


class Empeno(Base):
    __tablename__ = "empenos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_nombre = Column(String, nullable=False)
    cedula_cliente = Column(String, nullable=False)
    bien_prendario = Column(String, nullable=False)
    valor_tasacion = Column(Float, nullable=False)
    monto_prestado = Column(Float, nullable=False)
    tasa_interes_mensual = Column(Float, nullable=False, default=2.0)
    interes_generado = Column(Float, nullable=False)
    total_a_pagar = Column(Float, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento_inamovible = Column(Date, nullable=False)
    estado = Column(String, default="Activo")


class Dominio(Base):
    __tablename__ = "dominios"

    id = Column(Integer, primary_key=True, index=True)
    dominio = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    nombre_completo = Column(String, nullable=False)
    cliente = Column(String, nullable=False)
    contacto_correo = Column(String, nullable=False)
    precio_anual = Column(Float, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
