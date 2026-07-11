import os
import shutil
import tempfile
import logging
import re
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from markitdown import MarkItDown
import pytesseract
from pdf2image import convert_from_path

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("markitdown-web")

app = FastAPI(title="MarkItDown Web Service")

# Habilitar CORS por si se usa de forma remota
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta de salida montable para el servidor
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output")
if not os.path.isabs(OUTPUT_DIR):
    OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Instanciar MarkItDown de Microsoft
md = MarkItDown()

def clean_temp_file(path: str):
    """Elimina archivos temporales después de la respuesta HTTP."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Archivo temporal eliminado: {path}")
    except Exception as e:
        logger.error(f"Error eliminando archivo temporal {path}: {e}")

def is_scanned_pdf(text: str) -> bool:
    """
    Determina si un PDF está escaneado.
    Si la longitud de caracteres alfabéticos es extremadamente baja, asumimos que es una imagen.
    """
    if not text:
        return True
    alpha_chars = len(re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]', '', text))
    return alpha_chars < 150

def run_tesseract_ocr(pdf_path: str) -> str:
    """Convierte el PDF a imágenes y aplica Tesseract OCR en español e inglés."""
    logger.info(f"Iniciando Tesseract OCR local para: {pdf_path}")
    try:
        # Convertimos las páginas a imágenes con 150 DPI (buen balance velocidad/calidad)
        pages = convert_from_path(pdf_path, dpi=150)
        logger.info(f"PDF convertido a {len(pages)} imágenes para OCR")
        
        ocr_pages = []
        for i, page in enumerate(pages):
            logger.info(f"Procesando OCR página {i+1} de {len(pages)}...")
            text = pytesseract.image_to_string(page, lang='spa+eng')
            ocr_pages.append(f"## Página {i+1}\n\n{text.strip()}")
            
        return "\n\n".join(ocr_pages)
    except Exception as e:
        logger.error(f"Error ejecutando el OCR local: {e}")
        raise HTTPException(status_code=500, detail=f"Fallo en la tubería de OCR local: {str(e)}")

@app.post("/convert")
async def convert_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Recibe un archivo, lo convierte a Markdown y detecta si requiere OCR local."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = ['.pdf', '.docx', '.xlsx', '.xls', '.pptx', '.csv', '.json', '.xml', '.html', '.txt']
    
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}")

    # Crear archivo temporal con la misma extensión
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(temp_fd)

    try:
        # Copiar subida a archivo temporal
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Procesando conversión: {filename} ({ext})")
        
        # 1. Intentar conversión digital estándar
        result = md.convert(temp_path)
        extracted_text = result.text_content
        
        # 2. Si es PDF y está vacío o es imagen, aplicar OCR local
        ocr_applied = False
        if ext == '.pdf' and is_scanned_pdf(extracted_text):
            logger.info(f"El texto digital extraído es muy corto ({len(extracted_text)} caracteres). Aplicando OCR...")
            extracted_text = run_tesseract_ocr(temp_path)
            ocr_applied = True

        return JSONResponse(content={
            "filename": filename,
            "markdown": extracted_text,
            "ocr_applied": ocr_applied,
            "size_bytes": os.path.getsize(temp_path)
        })

    except Exception as e:
        logger.error(f"Error procesando {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la conversión: {str(e)}")
    finally:
        # Programar limpieza del archivo temporal
        background_tasks.add_task(clean_temp_file, temp_path)

@app.post("/save-server")
async def save_to_server(filename: str = Form(...), content: str = Form(...)):
    """Guarda el archivo Markdown directamente en la carpeta compartida del servidor."""
    # Sanitizar el nombre del archivo
    safe_filename = os.path.basename(filename)
    name, _ = os.path.splitext(safe_filename)
    safe_filename = f"{name}.md"
    
    target_path = os.path.join(OUTPUT_DIR, safe_filename)
    
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Archivo guardado con éxito en el servidor: {target_path}")
        return {
            "status": "success", 
            "path": target_path, 
            "filename": safe_filename,
            "server_folder": OUTPUT_DIR
        }
    except Exception as e:
        logger.error(f"Error guardando archivo en el servidor: {e}")
        raise HTTPException(status_code=500, detail=f"No se pudo guardar en el servidor: {str(e)}")

# Montar interfaz estática
# Determinar ruta del directorio estático
local_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(local_static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=local_static_dir, html=True), name="static")
