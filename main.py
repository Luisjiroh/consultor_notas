from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "notas.csv"

app = FastAPI(title="Consulta de Notas – Plan de Mercadeo")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def cargar_notas():
    """
    Lee el archivo notas.csv y devuelve un diccionario:
    {codigo: {"nombre": ..., "nota": ...}}
    """
    notas = {}
    if not DATA_FILE.exists():
        return notas

    with DATA_FILE.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = row["codigo"].strip()
            notas[codigo] = {
                "nombre": row.get("nombre", "").strip(),
                "nota": row.get("nota", "").strip(),
            }
    return notas


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Página principal con el formulario de consulta.
    También funcionará en Render si compartes esta URL directamente.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/nota")
async def consultar_nota(
    codigo: str = Query(..., description="Código o número de cédula del estudiante")
):
    """
    Endpoint para consultar la nota por código.
    Ejemplo de uso:
        /api/nota?codigo=12345678
    """
    notas = cargar_notas()
    codigo = codigo.strip()

    if codigo not in notas:
        return JSONResponse(
            {
                "encontrado": False,
                "mensaje": "No se encontró una nota para ese código.",
            },
            status_code=404,
        )

    info = notas[codigo]
    return {
        "encontrado": True,
        "codigo": codigo,
        "nombre": info["nombre"],
        "nota": info["nota"],
    }