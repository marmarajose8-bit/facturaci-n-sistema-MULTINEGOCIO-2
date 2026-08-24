# Modo offline/local - JG Facturaciones

Esto te deja correr el sistema completo en la computadora principal del
comercio (ej. la caja de un supermercado), sin depender de que haya
internet en ese momento. Las ventas se guardan localmente y se sincronizan
con la nube cuando vuelve la conexión.

## Requisitos

- Tener [Docker](https://docs.docker.com/get-docker/) instalado en esa PC.

## Cómo levantarlo

Desde la **raíz del proyecto** (no desde esta carpeta):

```bash
docker compose -f local-offline/docker-compose.yml up -d --build
```

Esto compila la imagen y levanta el sistema en `http://localhost:8000`.
Desde el navegador de esa PC, el panel visual queda en:

```
http://localhost:8000/panel/
```

Se usa exactamente igual que la versión en la nube - mismo login, mismo
panel - solo que corre en la máquina local, con su propia base de datos
SQLite (no ve ni comparte datos automáticamente con la nube; ver abajo
cómo sincronizar).

## Cómo funciona cuando no hay internet

1. El cajero factura normal, desde el panel local (`localhost:8000/panel/`).
2. Como no hay internet, esas ventas se guardan como **pendientes** (sin
   NCF todavía) - se le da al cliente un recibo provisional, no un
   comprobante fiscal.
3. Cuando vuelve el internet, hay que ir a la pestaña correspondiente en el
   panel (o llamar directamente a `POST /offline/sincronizar`) para que el
   sistema le asigne el NCF real a cada venta pendiente, en el orden en que
   ocurrieron, y las mande a la base de datos central en la nube.

**Importante:** este nodo local necesita las mismas credenciales del
comercio (RNC y contraseña) para iniciar sesión - son las mismas que se
usan en la versión de la nube, porque en el fondo es el mismo comercio.

## Actualizar el código local

Si actualizas el sistema en la nube (nuevas funciones), para que la copia
local también las tenga:

```bash
docker compose -f local-offline/docker-compose.yml down
docker compose -f local-offline/docker-compose.yml up -d --build
```

**Ojo:** el volumen de datos (`datos_locales`) se conserva entre reinicios
normales, así que no pierdes ventas guardadas. Pero si necesitas empezar
completamente de cero (por ejemplo, para pruebas), usa:

```bash
docker compose -f local-offline/docker-compose.yml down -v
```

Eso sí borra todo lo guardado localmente - solo úsalo si estás seguro.

## Por qué las ventas offline no tienen NCF hasta sincronizar

Los números de comprobante fiscal (NCF) tienen que ser estrictamente
consecutivos y únicos, según la DGII. Si el sistema local y el de la nube
generaran números por separado mientras no hay conexión, se duplicarían
o se desordenarían. Por eso las ventas offline se guardan sin número
fiscal, y solo se les asigna uno real cuando se sincronizan con la nube
(que es la única fuente de verdad para la secuencia).
