from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime
import csv

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "notas.csv"
LOG_FILE = BASE_DIR / "consultas_log.csv"

app = FastAPI(title="Consulta de Notas – Plan de Mercadeo")

# CORS para permitir llamadas desde Netlify u otros orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # si quieres, luego restringimos al dominio de Netlify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def cargar_notas():
    """
    Lee notas.csv y devuelve un diccionario:
    { codigo: {"nombre": ..., "nota": ...} }
    """
    notas = {}
    if not DATA_FILE.exists():
        return notas

    with DATA_FILE.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = (row.get("codigo") or "").strip()
            if not codigo:
                continue
            notas[codigo] = {
                "nombre": (row.get("nombre") or "").strip(),
                "nota": (row.get("nota") or "").strip(),
            }
    return notas


def registrar_consulta(
    request: Request,
    codigo: str,
    encontrado: bool,
):
    """
    Registra cada consulta en consultas_log.csv con:
    fecha_hora, codigo, encontrado, ip, user_agent
    """
    ahora = datetime.utcnow().isoformat(timespec="seconds") + "Z"  # UTC
    ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")

    nuevo_archivo = not LOG_FILE.exists()

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if nuevo_archivo:
            writer.writerow(
                ["fecha_hora_utc", "codigo", "encontrado", "ip", "user_agent"]
            )
        writer.writerow([ahora, codigo, "sí" if encontrado else "no", ip, user_agent])


@app.get("/", response_class=HTMLResponse)
async def home():
    # Solo una página sencilla para probar que el backend vive
    return """
    <html>
      <head><title>API Consulta Notas</title></head>
      <body>
        <h1>API Consulta de Notas – Plan de Mercadeo</h1>
        <p>Use el endpoint <code>/api/nota?codigo=...</code> para consultar.</p>
      </body>
    </html>
    """


@app.get("/api/nota")
async def consultar_nota(
    request: Request,
    codigo: str = Query(..., description="Código o número de cédula del estudiante"),
):
    notas = cargar_notas()
    codigo = codigo.strip()

    encontrado = codigo in notas

    # Registrar SIEMPRE la consulta (se encuentre o no)
    registrar_consulta(request, codigo, encontrado)

    if not encontrado:
        return JSONResponse(
            {
                "encontrado": False,
                "mensaje": "No se encontró una nota para ese número de cédula.",
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


@app.get("/admin/consultas", response_class=HTMLResponse)
async def ver_consultas():
    """
    Muestra en HTML simple el contenido de consultas_log.csv
    Solo informativo para ti como docente.
    """
    if not LOG_FILE.exists():
        return HTMLResponse(
            "<h2>No hay registros de consultas todavía.</h2>",
            status_code=200,
        )

    rows = []
    with LOG_FILE.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return "<h2>El archivo de log está vacío.</h2>"

    # Primera fila = encabezados
    headers = rows[0]
    data_rows = rows[1:]

    # Construimos una tabla HTML sencilla
    table_headers = "".join(f"<th>{h}</th>" for h in headers)
    table_rows = ""
    for r in data_rows:
        tds = "".join(f"<td>{c}</td>" for c in r)
        table_rows += f"<tr>{tds}</tr>"

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Log de consultas</title>
        <style>
          body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            padding: 16px;
            background: #f5f6fb;
          }}
          h1 {{
            margin-bottom: 10px;
          }}
          table {{
            border-collapse: collapse;
            width: 100%;
            background: #fff;
          }}
          th, td {{
            border: 1px solid #d0d3e3;
            padding: 6px 8px;
            font-size: 0.86rem;
          }}
          th {{
            background: #e4e7f7;
            text-align: left;
          }}
          tr:nth-child(even) td {{
            background: #fafbff;
          }}
        </style>
      </head>
      <body>
        <h1>Registro de consultas de notas</h1>
        <p>Este listado es solo informativo para el docente.</p>
        <table>
          <thead><tr>{table_headers}</tr></thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
      </body>
    </html>
    """
    return HTMLResponse(html)