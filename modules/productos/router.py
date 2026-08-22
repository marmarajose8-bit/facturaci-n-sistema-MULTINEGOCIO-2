from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from core.models import Producto, Comercio
from core.deps import get_comercio_actual

router = APIRouter(prefix="/productos", tags=["Inventario (Productos)"])


class RegistroProducto(BaseModel):
    nombre: str
    precio_unitario: float
    stock_actual: int = 0
    stock_minimo: int = 0
    codigo_barras: Optional[str] = None


class ActualizarProducto(BaseModel):
    nombre: Optional[str] = None
    precio_unitario: Optional[float] = None
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None
    codigo_barras: Optional[str] = None


@router.post("")
def registrar_producto(
    datos: RegistroProducto,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    if datos.codigo_barras:
        existente = (
            db.query(Producto)
            .filter(Producto.comercio_id == comercio_actual.id, Producto.codigo_barras == datos.codigo_barras)
            .first()
        )
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya tienes un producto con el código de barras {datos.codigo_barras}")

    producto = Producto(
        comercio_id=comercio_actual.id,
        codigo_barras=datos.codigo_barras,
        nombre=datos.nombre,
        precio_unitario=datos.precio_unitario,
        stock_actual=datos.stock_actual,
        stock_minimo=datos.stock_minimo,
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)

    return {
        "estado": "Producto Registrado",
        "id": producto.id,
        "nombre": producto.nombre,
        "precio_unitario": producto.precio_unitario,
        "stock_actual": producto.stock_actual,
    }


@router.get("")
def listar_productos(
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    productos = (
        db.query(Producto)
        .filter(Producto.comercio_id == comercio_actual.id, Producto.activo == "si")
        .order_by(Producto.nombre)
        .all()
    )
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "codigo_barras": p.codigo_barras,
            "precio_unitario": p.precio_unitario,
            "stock_actual": p.stock_actual,
            "stock_minimo": p.stock_minimo,
            "bajo_stock": p.stock_actual <= p.stock_minimo,
        }
        for p in productos
    ]


@router.put("/{producto_id}")
def actualizar_producto(
    producto_id: int,
    datos: ActualizarProducto,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    producto = (
        db.query(Producto)
        .filter(Producto.id == producto_id, Producto.comercio_id == comercio_actual.id)
        .first()
    )
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if datos.nombre is not None:
        producto.nombre = datos.nombre
    if datos.precio_unitario is not None:
        producto.precio_unitario = datos.precio_unitario
    if datos.stock_actual is not None:
        producto.stock_actual = datos.stock_actual
    if datos.stock_minimo is not None:
        producto.stock_minimo = datos.stock_minimo
    if datos.codigo_barras is not None:
        producto.codigo_barras = datos.codigo_barras

    db.add(producto)
    db.commit()
    db.refresh(producto)

    return {
        "estado": "Producto Actualizado",
        "id": producto.id,
        "nombre": producto.nombre,
        "precio_unitario": producto.precio_unitario,
        "stock_actual": producto.stock_actual,
    }


@router.delete("/{producto_id}")
def desactivar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    producto = (
        db.query(Producto)
        .filter(Producto.id == producto_id, Producto.comercio_id == comercio_actual.id)
        .first()
    )
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = "no"
    db.add(producto)
    db.commit()

    return {"estado": "Producto Desactivado", "id": producto.id, "nombre": producto.nombre}
