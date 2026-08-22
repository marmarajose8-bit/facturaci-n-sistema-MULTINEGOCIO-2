from datetime import date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.settings import MONEDA, ITBIS_GENERAL
from core.database import get_db
from core.models import Factura, DetalleFactura, Comercio, SecuenciaNCF, Empleado, Producto
from core.deps import get_comercio_actual
from core.security import verify_password

router = APIRouter(prefix="/pos", tags=["POS y Facturación - RD"])


class DetalleItem(BaseModel):
    producto_id: Optional[int] = None  # si se manda, se descuenta del inventario y se usa el precio/nombre del catálogo
    descripcion: Optional[str] = None  # requerido solo si NO se manda producto_id (línea libre)
    cantidad: int
    precio_unitario: Optional[float] = None  # requerido solo si NO se manda producto_id


class FacturaRD(BaseModel):
    tipo_ncf: str  # Ej: "B02" (Consumo), "B01" (Crédito Fiscal) - el NCF lo genera el sistema
    cliente: str
    rnc_cedula: str
    items: List[DetalleItem]
    metodo_pago: str  # Efectivo, Transferencia, Tarjeta
    pin_empleado: Optional[str] = None  # opcional: identifica qué cajero hizo la venta


def _siguiente_ncf(comercio_id: int, tipo_ncf: str, db: Session) -> str:
    """
    Toma el próximo número disponible de la secuencia NCF autorizada por la DGII
    para este comercio y tipo de comprobante, valida rango y vencimiento, y avanza
    el contador. Esto es lo que hace que el número de factura sea fiscalmente válido.
    """
    secuencia = (
        db.query(SecuenciaNCF)
        .filter(SecuenciaNCF.comercio_id == comercio_id, SecuenciaNCF.tipo_ncf == tipo_ncf)
        .first()
    )
    if not secuencia:
        raise HTTPException(
            status_code=400,
            detail=f"No tienes una secuencia NCF autorizada para el tipo '{tipo_ncf}'. "
                   f"Regístrala primero en POST /comercios/secuencias-ncf",
        )
    if secuencia.activa != "si":
        raise HTTPException(status_code=400, detail=f"Tu secuencia NCF '{tipo_ncf}' está inactiva")
    if secuencia.fecha_vencimiento < date.today():
        raise HTTPException(
            status_code=400,
            detail=f"Tu secuencia NCF '{tipo_ncf}' venció el {secuencia.fecha_vencimiento}. "
                   f"Hay que solicitar una nueva autorización a la DGII.",
        )
    if secuencia.secuencia_actual > secuencia.secuencia_hasta:
        raise HTTPException(
            status_code=400,
            detail=f"Tu secuencia NCF '{tipo_ncf}' se agotó. Hay que solicitar un nuevo rango a la DGII.",
        )

    ncf = f"{tipo_ncf}{secuencia.secuencia_actual:08d}"
    secuencia.secuencia_actual += 1
    db.add(secuencia)
    return ncf


def _identificar_empleado(comercio_id: int, pin: Optional[str], db: Session) -> Optional[Empleado]:
    if not pin:
        return None
    activos = (
        db.query(Empleado)
        .filter(Empleado.comercio_id == comercio_id, Empleado.activo == "si")
        .all()
    )
    for e in activos:
        if verify_password(pin, e.pin_hash):
            return e
    raise HTTPException(status_code=400, detail="PIN de empleado incorrecto o inactivo")


def _procesar_items(comercio_id: int, items: List[DetalleItem], db: Session):
    """
    Valida cada línea de la factura. Si trae producto_id: busca el producto,
    confirma que hay stock suficiente, y prepara el descuento (no lo aplica
    todavía, para no tocar la base de datos si alguna línea posterior falla).
    Si no trae producto_id: es una línea libre (requiere descripcion y precio).
    Devuelve la lista de DetalleFactura listos para guardar y la lista de
    productos a descontar.
    """
    detalles = []
    productos_a_descontar = []  # (producto, cantidad)

    for item in items:
        if item.producto_id:
            producto = (
                db.query(Producto)
                .filter(Producto.id == item.producto_id, Producto.comercio_id == comercio_id, Producto.activo == "si")
                .first()
            )
            if not producto:
                raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
            if producto.stock_actual < item.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente de '{producto.nombre}': quedan {producto.stock_actual}, se pidieron {item.cantidad}",
                )
            detalles.append(DetalleFactura(
                producto_id=producto.id,
                descripcion=producto.nombre,
                cantidad=item.cantidad,
                precio_unitario=producto.precio_unitario,
            ))
            productos_a_descontar.append((producto, item.cantidad))
        else:
            if not item.descripcion or item.precio_unitario is None:
                raise HTTPException(
                    status_code=400,
                    detail="Cada línea sin producto_id necesita descripcion y precio_unitario",
                )
            detalles.append(DetalleFactura(
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            ))

    return detalles, productos_a_descontar


@router.post("/emitir-factura-rd")
def emitir_factura_rd(
    datos: FacturaRD,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    ncf_generado = _siguiente_ncf(comercio_actual.id, datos.tipo_ncf, db)
    empleado = _identificar_empleado(comercio_actual.id, datos.pin_empleado, db)
    detalles, productos_a_descontar = _procesar_items(comercio_actual.id, datos.items, db)

    subtotal = sum(d.cantidad * d.precio_unitario for d in detalles)
    itbis = subtotal * ITBIS_GENERAL
    total_con_itbis = subtotal + itbis

    factura = Factura(
        comercio_id=comercio_actual.id,
        empleado_id=empleado.id if empleado else None,
        nro_factura=ncf_generado,
        tipo_ncf=datos.tipo_ncf,
        cliente=datos.cliente,
        rnc_cedula=datos.rnc_cedula,
        subtotal=round(subtotal, 2),
        itbis=round(itbis, 2),
        total_pagar=round(total_con_itbis, 2),
        metodo_pago=datos.metodo_pago,
    )
    factura.items = detalles

    # Ahora que sabemos que toda la factura es válida, descontamos el stock
    for producto, cantidad in productos_a_descontar:
        producto.stock_actual -= cantidad
        db.add(producto)

    db.add(factura)
    db.commit()
    db.refresh(factura)

    return {
        "entidad": comercio_actual.nombre_comercial,
        "estado": "Factura Fiscal Generada",
        "ncf": factura.nro_factura,
        "tipo_ncf": factura.tipo_ncf,
        "cliente": factura.cliente,
        "rnc_cedula": factura.rnc_cedula,
        "subtotal": factura.subtotal,
        "itbis_18": factura.itbis,
        "total_pagar": factura.total_pagar,
        "moneda": MONEDA,
        "metodo_pago": factura.metodo_pago,
        "atendido_por": empleado.nombre if empleado else None,
    }


@router.get("/facturas")
def listar_facturas(
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    facturas = (
        db.query(Factura)
        .filter(Factura.comercio_id == comercio_actual.id)
        .order_by(Factura.id.desc())
        .all()
    )
    return [
        {
            "ncf": f.nro_factura,
            "tipo_ncf": f.tipo_ncf,
            "cliente": f.cliente,
            "total_pagar": f.total_pagar,
            "metodo_pago": f.metodo_pago,
            "fecha_emision": f.fecha_emision,
            "atendido_por": f.empleado.nombre if f.empleado else None,
        }
        for f in facturas
    ]


@router.get("/facturas/{ncf}")
def obtener_factura(
    ncf: str,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    factura = (
        db.query(Factura)
        .filter(Factura.comercio_id == comercio_actual.id, Factura.nro_factura == ncf)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    return {
        "entidad": comercio_actual.nombre_comercial,
        "ncf": factura.nro_factura,
        "tipo_ncf": factura.tipo_ncf,
        "cliente": factura.cliente,
        "rnc_cedula": factura.rnc_cedula,
        "subtotal": factura.subtotal,
        "itbis_18": factura.itbis,
        "total_pagar": factura.total_pagar,
        "moneda": MONEDA,
        "metodo_pago": factura.metodo_pago,
        "atendido_por": factura.empleado.nombre if factura.empleado else None,
        "items": [
            {
                "descripcion": item.descripcion,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "producto_id": item.producto_id,
            }
            for item in factura.items
        ],
    }
