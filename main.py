from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import csv

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "notas.csv"
LOG_FILE = BASE_DIR / "consultas.csv"

app = FastAPI(title="Consulta de Notas – Plan de Mercadeo")

# CORS para permitir llamadas desde Netlify u otros frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # si quieres, luego lo restringimos al dominio de Netlify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def registrar_consulta(
    codigo: str,
    encontrado: bool,
    nombre: str,
    request: Request,
):
    """
    Registra cada consulta en consultas.csv
    Columnas: timestamp, codigo, encontrado, nombre, ip, user_agent
    """
    timestamp = datetime.now().isoformat(timespec="seconds")

    # IP del cliente
    client_ip = request.client.host if request.client else ""

    # User-Agent del navegador (si viene en los headers)
    user_agent = request.headers.get("user-agent", "")

    file_exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["timestamp", "codigo", "encontrado", "nombre", "ip", "user_agent"]
            )
        writer.writerow(
            [timestamp, codigo, str(encontrado), nombre, client_ip, user_agent]
        )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Esta ruta casi no la usas porque el frontend está en Netlify,
    # pero la dejamos como página simple de estado.
    html = """
    <html>
      <head><title>Consulta de Notas – Backend</title></head>
      <body>
        <h1>Backend de Consulta de Notas está en línea ✅</h1>
        <p>Use la ruta <code>/api/nota?codigo=...</code> desde el frontend.</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/nota")
async def consultar_nota(
    request: Request,
    codigo: str = Query(..., description="Código o número de cédula del estudiante"),
):
    notas = cargar_notas()
    codigo = codigo.strip()

    if codigo not in notas:
        # Registramos la consulta aunque no se encuentre
        registrar_consulta(codigo=codigo, encontrado=False, nombre="", request=request)
        return JSONResponse(
            {
                "encontrado": False,
                "mensaje": "No se encontró una nota para ese número de cédula.",
            },
            status_code=404,
        )

    info = notas[codigo]
    registrar_consulta(codigo=codigo, encontrado=True, nombre=info["nombre"], request=request)

    return {
        "encontrado": True,
        "codigo": codigo,
        "nombre": info["nombre"],
        "nota": info["nota"],
    }