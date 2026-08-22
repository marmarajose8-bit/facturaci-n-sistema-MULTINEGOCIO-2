from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from core.database import Base


class Comercio(Base):
    """Cada comercio (tenant) que contrata el SaaS. Todo lo demás cuelga de aquí."""
    __tablename__ = "comercios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_comercial = Column(String, nullable=False)
    rnc = Column(String, unique=True, index=True, nullable=False)
    email_contacto = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="basico")
    activo = Column(String, default="si")  # "si" / "no" - simple por ahora, sin lógica de suspensión aún
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    facturas = relationship("Factura", back_populates="comercio")
    empenos = relationship("Empeno", back_populates="comercio")
    dominios = relationship("Dominio", back_populates="comercio")
    secuencias_ncf = relationship("SecuenciaNCF", back_populates="comercio")
    empleados = relationship("Empleado", back_populates="comercio")
    productos = relationship("Producto", back_populates="comercio")


class SecuenciaNCF(Base):
    """
    Rango de Números de Comprobante Fiscal (NCF) que la DGII autorizó a un comercio
    para un tipo de comprobante específico (ej. B02 = Consumo, B01 = Crédito Fiscal).
    El sistema consume esta secuencia automáticamente, nunca se escribe a mano.
    """
    __tablename__ = "secuencias_ncf"
    __table_args__ = (
        UniqueConstraint("comercio_id", "tipo_ncf", name="uq_comercio_tipo_ncf"),
    )

    id = Column(Integer, primary_key=True, index=True)
    comercio_id = Column(Integer, ForeignKey("comercios.id"), nullable=False, index=True)
    tipo_ncf = Column(String, nullable=False)  # Ej: "B02" (Consumo), "B01" (Crédito Fiscal), "B14" (Regímenes Especiales)
    descripcion = Column(String, nullable=True)
    secuencia_desde = Column(Integer, nullable=False)
    secuencia_hasta = Column(Integer, nullable=False)
    secuencia_actual = Column(Integer, nullable=False)  # próximo número a emitir
    fecha_vencimiento = Column(Date, nullable=False)
    activa = Column(String, default="si")

    comercio = relationship("Comercio", back_populates="secuencias_ncf")


class Empleado(Base):
    """
    Cajero o empleado de un comercio. No tiene login completo (usuario/contraseña) -
    usa un PIN corto para identificarse al hacer una venta, como en una caja
    registradora física. El dueño del comercio (con su sesión JWT) es quien da de
    alta a los empleados.
    """
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    comercio_id = Column(Integer, ForeignKey("comercios.id"), nullable=False, index=True)
    nombre = Column(String, nullable=False)
    pin_hash = Column(String, nullable=False)
    rol = Column(String, default="cajero")  # "cajero" o "admin"
    activo = Column(String, default="si")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    comercio = relationship("Comercio", back_populates="empleados")


class Producto(Base):
    """
    Artículo del catálogo/inventario de un comercio. Cuando una factura vende un
    producto (en vez de una línea de texto libre), el stock se descuenta
    automáticamente y no se permite vender más de lo que hay disponible.
    """
    __tablename__ = "productos"
    __table_args__ = (
        UniqueConstraint("comercio_id", "codigo_barras", name="uq_producto_comercio_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    comercio_id = Column(Integer, ForeignKey("comercios.id"), nullable=False, index=True)
    codigo_barras = Column(String, nullable=True)  # opcional, único por comercio si se usa
    nombre = Column(String, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    stock_actual = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, nullable=False, default=0)  # para avisar cuándo reponer
    activo = Column(String, default="si")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    comercio = relationship("Comercio", back_populates="productos")


class Factura(Base):
    __tablename__ = "facturas"
    __table_args__ = (
        UniqueConstraint("comercio_id", "nro_factura", name="uq_factura_comercio_nro"),
    )

    id = Column(Integer, primary_key=True, index=True)
    comercio_id = Column(Integer, ForeignKey("comercios.id"), nullable=False, index=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)  # quién la emitió, si se identificó con PIN
    nro_factura = Column(String, index=True, nullable=False)  # el NCF real generado por el sistema, ej. B0200000001
    tipo_ncf = Column(String, nullable=False)
    cliente = Column(String, nullable=False)
    rnc_cedula = Column(String, nullable=False)
    subtotal = Column(Float, nullable=False)
    itbis = Column(Float, nullable=False)
    total_pagar = Column(Float, nullable=False)
    metodo_pago = Column(String, nullable=False)
    fecha_emision = Column(DateTime, default=datetime.utcnow)

    comercio = relationship("Comercio", back_populates="facturas")
    empleado = relationship("Empleado")
    items = relationship(
        "DetalleFactura", back_populates="factura", cascade="all, delete-orphan"
    )


class DetalleFactura(Base):
    __tablename__ = "detalle_facturas"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)  # si se vendió del inventario
    descripcion = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)

    factura = relationship("Factura", back_populates="items")
    producto = relationship("Producto")


class Empeno(Base):
    __tablename__ = "empenos"

    id = Column(Integer, primary_key=True, index=True)
    comercio_id = Column(Integer, ForeignKey("comercios.id"), nullable=False, index=True)
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

    comercio = relationship("Comercio", back_populates="empenos")


class Dominio(Base):
    __tablename__ = "dominios"

    id = Column(Integer, primary_key=True, index=True)
    comercio_id = Column(Integer, ForeignKey("comercios.id"), nullable=False, index=True)
    dominio = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    nombre_completo = Column(String, nullable=False)
    cliente = Column(String, nullable=False)
    contacto_correo = Column(String, nullable=False)
    precio_anual = Column(Float, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    comercio = relationship("Comercio", back_populates="dominios")
