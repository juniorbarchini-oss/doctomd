# DocToMD Web Service (RAG-Ready)

Este proyecto es un microservicio web de código abierto diseñado para auto-alojarse en un servidor local (vía Docker o Portainer) o ejecutarse localmente. Permite convertir cualquier documento de oficina en texto **Markdown** limpio y estructurado, listo para alimentar tuberías de **RAG (Retrieval-Augmented Generation)** o tu gestor de notas.

## 💻 Sistemas Operativos Soportados
*   **macOS** (Soporte nativo local)
*   **Linux** (Soporte nativo local y vía Docker)
*   **Windows** (Soporte vía Docker o WSL)

## Características Clave
- **Formatos soportados:** PDF (digitales y escaneados), Word (`.docx`), Excel (`.xlsx` / `.xls`), PowerPoint (`.pptx`), HTML, CSV, JSON, XML y TXT.
- **OCR local integrado:** Si subes un PDF escaneado (que sea solo imagen), el backend lo detecta y le aplica automáticamente **Tesseract OCR** en español e inglés sin enviar datos a APIs externas.
- **Guardado en Servidor:** Puedes configurar una ruta compartida en tu servidor (volumen Docker `/app/output`) y guardar los resultados directamente con un solo clic.
- **Cola de procesamiento en lote:** Arrastra múltiples archivos simultáneamente; se procesarán uno por uno para cuidar la CPU del servidor, y podrás descargar todos juntos compilados en un `.zip`.
- **Interfaz Premium:** Diseño moderno en modo oscuro con vista doble (código raw Markdown a la izquierda, renderizado visual a la derecha).

---

## Estructura del Proyecto
```text
doctomd/
├── main.py                  # API Backend (FastAPI + MarkItDown + Tesseract)
├── requirements.txt         # Dependencias Python
├── Dockerfile               # Construcción del contenedor multi-stage
├── docker-compose.yml       # Orquestación Docker
├── README.md                # Esta guía técnica
└── static/
    └── index.html           # Interfaz de usuario Single Page App (HTML/CSS/JS)
```

---

## Requisitos de Instalación Local (macOS / Linux)

Si deseas correr la aplicación directamente en tu equipo en lugar de Docker:

1. **Instalar dependencias del sistema:**
   Necesitas instalar Tesseract (motor de OCR) con soporte en español y Poppler (para convertir PDF a imágenes). 
   *   **En macOS (con Homebrew):**
       ```bash
       brew install tesseract tesseract-lang poppler
       ```
   *   **En Linux (Debian/Ubuntu):**
       ```bash
       sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-spa poppler-utils
       ```

2. **Inicializar Entorno Virtual:**
   ```bash
   cd doctomd
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias de Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar el Servidor Local:**
   ```bash
   uvicorn main:app --reload --port 8490
   ```
   Abre tu navegador en: [http://localhost:8490](http://localhost:8490)

---

## Despliegue en Portainer / Docker

Para desplegar este servicio en tu propio servidor mediante Portainer como un **Stack** o directamente vía CLI:

### 1. Definición del docker-compose.yml
Puedes copiar este contenido directamente en el editor web de Stacks en Portainer o crearlo localmente:

```yaml
version: '3.8'

services:
  doctomd:
    build:
      context: .
    container_name: doctomd-service
    ports:
      - "8490:8490"
    volumes:
      # Mapea esta carpeta a la ruta donde quieres recibir los Markdown (ej: tu Bóveda de Obsidian o un recurso compartido de red)
      - /ruta/de/tu/servidor/output:/app/output
    restart: unless-stopped
    environment:
      - TZ=America/Asuncion
```

### 2. Mapeo de Volúmenes en el Servidor
- El contenedor expone la ruta `/app/output`. Cuando haces clic en **"Guardar en Servidor"** desde la interfaz web, el archivo Markdown se guarda allí.
- Te recomendamos mapear esta carpeta de tu servidor a una carpeta de red que sincronices con tu Obsidian, de esta forma las conversiones aparecerán instantáneamente en tu aplicación de notas.

---

## Detalles del Motor de OCR
- El backend utiliza `pdf2image` para rasterizar las páginas a 150 DPI y alimentar a `pytesseract`.
- El parámetro utilizado en Tesseract es `lang='spa+eng'` para soportar texto bilingüe y reconocer caracteres con tildes y eñes correctamente.
- La detección del PDF escaneado se hace mediante un algoritmo de conteo de caracteres alfabéticos sobre la primera extracción de `markitdown`. Si hay menos de 150 caracteres en total, se activa la tubería de OCR automáticamente.
