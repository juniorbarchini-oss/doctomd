# Etapa 1: Compilación y dependencias de Python
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar dependencias para compilar posibles extensiones de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Etapa 2: Imagen de ejecución ligera
FROM python:3.11-slim AS runner

WORKDIR /app

# Instalar dependencias del sistema indispensables para:
# - Tesseract OCR (Reconocimiento óptico de caracteres en español e inglés)
# - Poppler (Requerido por pdf2image para renderizar páginas de PDF a imágenes)
# - Libgl1 (Para dependencias gráficas/procesamiento de imágenes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar las librerías instaladas en la etapa anterior
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copiar el código fuente
COPY . .

# Crear el directorio de salida para guardar las conversiones en el servidor
RUN mkdir -p /app/output && chmod 777 /app/output

# Puerto de escucha
EXPOSE 8490

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8490"]
