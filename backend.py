#!/usr/bin/env python3.11
"""
EscalaFácil Backend — FastAPI simples que recebe FormData
e chama o pipeline Python de extração de PDF.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys
import json
import base64
import tempfile
import subprocess
from pathlib import Path

app = FastAPI()

# CORS para aceitar requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Armazenar sessões em memória
sessions = {}

def executar_python(args):
    """Executa script Python e retorna JSON."""
    script_path = os.path.join(os.path.dirname(__file__), "pdf_pipeline", "cli.py")
    
    # Limpar PYTHONHOME
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env["PYTHONPATH"] = os.path.dirname(__file__)
    
    proc = subprocess.run(
        [sys.executable, script_path] + args,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
        env=env,
        timeout=60
    )
    
    if proc.returncode != 0:
        print(f"[PYTHON ERROR] {proc.stderr}")
        raise Exception(f"Erro ao processar PDF: {proc.stderr}")
    
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        print(f"[PYTHON OUTPUT] {proc.stdout}")
        raise Exception("Resposta inválida do servidor Python")

@app.post("/processar")
async def processar(pdf: UploadFile = File(...), nome: str = Form(...)):
    """
    Recebe PDF + nome do profissional
    Retorna top 3 matches com percentual de similaridade
    """
    try:
        # Salvar PDF temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await pdf.read()
            tmp.write(content)
            pdf_path = tmp.name
        
        print(f"[UPLOAD] PDF salvo em: {pdf_path}")
        print(f"[UPLOAD] Tamanho: {len(content)} bytes")
        print(f"[UPLOAD] Nome: {nome}")
        
        # Executar pipeline Python
        resultado = executar_python(["processar", pdf_path, nome])
        
        # Criar sessão
        session_id = base64.b64encode(os.urandom(12)).decode()
        sessions[session_id] = {
            "pdf_path": pdf_path,
            "resultado": resultado
        }
        
        print(f"[PROCESSAR] Session ID: {session_id}")
        print(f"[PROCESSAR] Matches: {len(resultado.get('matches', []))}")
        
        return {
            "session_id": session_id,
            "matches": resultado.get("matches", []),
            "total_profissionais": resultado.get("total_profissionais", 0)
        }
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/confirmar")
async def confirmar(session_id: str = Form(...), nome_escolhido: str = Form(...)):
    """
    Recebe session_id + nome escolhido
    Retorna plantões estruturados
    """
    try:
        if session_id not in sessions:
            raise Exception("Sessão não encontrada ou expirada")
        
        session = sessions[session_id]
        pdf_path = session["pdf_path"]
        
        print(f"[CONFIRMAR] Session ID: {session_id}")
        print(f"[CONFIRMAR] Nome escolhido: {nome_escolhido}")
        
        # Executar confirmação
        resultado = executar_python(["confirmar", pdf_path, nome_escolhido, "0", "0"])
        
        print(f"[CONFIRMAR] Plantões: {len(resultado.get('plantoes', []))}")
        print(f"[CONFIRMAR] Extras: {len(resultado.get('extras', []))}")
        
        # Calcular total de horas
        total_horas = 0
        for p in resultado.get("plantoes", []) + resultado.get("extras", []):
            if p.get("inicio") and p.get("fim"):
                # Simplificado: apenas contar como 12h se houver horário
                total_horas += 12
        
        return {
            "profissional": nome_escolhido,
            "base": resultado.get("base", ""),
            "plantoes": resultado.get("plantoes", []),
            "extras": resultado.get("extras", []),
            "folgas": resultado.get("folgas", []),
            "total_horas": total_horas
        }
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Redireciona para o index.html"""
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    
    # Copiar pipeline Python se não existir
    if not os.path.exists("pdf_pipeline"):
        print("[SETUP] Copiando pipeline Python...")
        os.system("cp -r /home/ubuntu/escalafacil/server/pdf_pipeline .")
    
    print("[STARTUP] Iniciando servidor FastAPI na porta 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
