# Este Dockerfile es SOLO para correr el sistema en la PC de un comercio, sin
# internet. Railway NUNCA usa este archivo - está fuera de la raíz del repo
# a propósito, para que Railway (que usa Nixpacks vía railway.json) no se
# confunda con él, como pasó cuando había un Dockerfile en la raíz.
#
# IMPORTANTE: este build se corre desde la RAÍZ del proyecto, no desde esta
# carpeta, para que pueda copiar todo el código. Ver instrucciones en
# local-offline/README.md

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# En modo local, sin DATABASE_URL, el sistema usa SQLite automáticamente -
# igual que en las pruebas que hicimos durante el desarrollo.
ENV DATABASE_URL=""

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
