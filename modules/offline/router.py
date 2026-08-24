import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import VentaPendiente, Comercio
from core.deps import get_comercio_actual
from modules.pos.router import FacturaRD, emitir_factura_interno

router = APIRouter(prefix="/offline", tags=["Modo Offline (Sincronización)"])


@router.post("/venta-local")
def registrar_venta_local(
    datos: FacturaRD,
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    """
    Registra una venta hecha SIN conexión a la nube central (por ejemplo, corriendo
    en el nodo local Docker de un supermercado con el internet caído). No genera
    NCF todavía - eso solo se hace al sincronizar, para nunca duplicar números.
    El recibo que se le da al cliente aquí es PROVISIONAL, no un comprobante
    fiscal válido hasta que se sincronice con éxito.
    """
    pendientes_previas = (
        db.query(VentaPendiente)
        .filter(VentaPendiente.comercio_id == comercio_actual.id)
        .count()
    )
    recibo_provisional = f"OFFLINE-{pendientes_previas + 1:06d}"

    venta = VentaPendiente(
        comercio_id=comercio_actual.id,
        recibo_provisional=recibo_provisional,
        datos_json=datos.model_dump_json(),
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)

    return {
        "estado": "Venta guardada localmente (pendiente de sincronizar)",
        "recibo_provisional": venta.recibo_provisional,
        "aviso": "Este NO es un comprobante fiscal válido todavía. Se convertirá en factura con NCF real cuando se sincronice con internet.",
        "cliente": datos.cliente,
    }


@router.get("/pendientes")
def listar_pendientes(
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    pendientes = (
        db.query(VentaPendiente)
        .filter(VentaPendiente.comercio_id == comercio_actual.id, VentaPendiente.sincronizado == "no")
        .order_by(VentaPendiente.id.asc())
        .all()
    )
    return [
        {
            "id": v.id,
            "recibo_provisional": v.recibo_provisional,
            "fecha_creacion": v.fecha_creacion,
            "error_sincronizacion": v.error_sincronizacion,
        }
        for v in pendientes
    ]


@router.post("/sincronizar")
def sincronizar(
    db: Session = Depends(get_db),
    comercio_actual: Comercio = Depends(get_comercio_actual),
):
    """
    Recorre las ventas offline pendientes de ESTE comercio, en el mismo orden en
    que ocurrieron, y las convierte en facturas fiscales reales con NCF - una por
    una. Si alguna falla (ej. se agotó la secuencia NCF), se detiene ahí mismo
    para no desordenar el orden de las que faltan, y las reporta como error para
    reintentar después de resolver la causa.
    """
    pendientes = (
        db.query(VentaPendiente)
        .filter(VentaPendiente.comercio_id == comercio_actual.id, VentaPendiente.sincronizado == "no")
        .order_by(VentaPendiente.id.asc())
        .all()
    )

    sincronizadas = []
    errores = []

    for venta in pendientes:
        try:
            datos_dict = json.loads(venta.datos_json)
            datos = FacturaRD(**datos_dict)
            resultado = emitir_factura_interno(comercio_actual, datos, db)

            venta.sincronizado = "si"
            venta.ncf_resultante = resultado["ncf"]
            venta.error_sincronizacion = None
            db.add(venta)
            db.commit()

            sincronizadas.append({
                "recibo_provisional": venta.recibo_provisional,
                "ncf_asignado": resultado["ncf"],
            })
        except HTTPException as e:
            db.rollback()
            venta.error_sincronizacion = str(e.detail)
            db.add(venta)
            db.commit()
            errores.append({"recibo_provisional": venta.recibo_provisional, "error": str(e.detail)})
            break  # nos detenemos para no desordenar el resto de la cola
        except Exception as e:
            db.rollback()
            venta.error_sincronizacion = f"Error inesperado: {str(e)}"
            db.add(venta)
            db.commit()
            errores.append({"recibo_provisional": venta.recibo_provisional, "error": str(e)})
            break

    return {
        "sincronizadas": len(sincronizadas),
        "detalle_sincronizadas": sincronizadas,
        "con_error": len(errores),
        "detalle_errores": errores,
        # Las que dieron error NO se marcan como sincronizadas - siguen pendientes,
        # por eso no se restan aparte, solo lo ya sincronizado con éxito.
        "quedan_pendientes": len(pendientes) - len(sincronizadas),
    }
