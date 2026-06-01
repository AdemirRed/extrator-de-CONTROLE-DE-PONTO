"""
Ponto de entrada do servidor FastAPI.
Execute: python main.py   ou   iniciar.bat
Acesse:  http://localhost:8000

Todos os dados sao salvos em database/ponto.json
"""

import sys
import webbrowser
import threading
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.storage import load, save
from backend.routes.funcionarios  import router as r_func
from backend.routes.registros     import router as r_reg
from backend.routes.ocr_route     import router as r_ocr
from backend.routes.exports_route import router as r_exp
from backend.routes.feriados      import router as r_fer
from backend.routes.config_route  import router as r_cfg
from backend.routes.importar      import router as r_imp
from backend.routes.state_route   import router as r_state
from backend.routes.backup_route  import router as r_backup
from backend.routes.exportar      import router as r_export
from backend.routes.ia_route       import router as r_ia

app = FastAPI(title="Sistema de Cartao Ponto", version="2.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(r_func)
app.include_router(r_reg)
app.include_router(r_ocr)
app.include_router(r_exp)
app.include_router(r_fer)
app.include_router(r_cfg)
app.include_router(r_imp)
app.include_router(r_state)
app.include_router(r_backup)
app.include_router(r_export)
app.include_router(r_ia)

FRONTEND_DIR = Path(__file__).parent / "frontend"
ROOT_DIR     = Path(__file__).parent

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# Middleware para desabilitar cache em desenvolvimento
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)


@app.get("/")
def index():
    # Sempre serve o frontend/index.html atualizado
    return FileResponse(
        str(FRONTEND_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate",
                 "Pragma": "no-cache", "Expires": "0"}
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    print("=" * 50)
    print("  SISTEMA DE CARTAO PONTO v2.0")
    print("=" * 50)

    # Garante que o arquivo JSON existe
    Path("database").mkdir(exist_ok=True)
    Path("uploads").mkdir(exist_ok=True)
    Path("exports").mkdir(exist_ok=True)
    d = load()
    save(d)
    print("OK Dados carregados de database/ponto.json")

    HOST, PORT = "127.0.0.1", 8000
    print(f"OK Servidor em http://{HOST}:{PORT}")
    print("   Ctrl+C para encerrar\n")

    threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
