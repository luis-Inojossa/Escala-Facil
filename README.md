# EscalaFácil — Consulte seus plantões do SAMU

Aplicação web para extrair e consultar plantões de profissionais do SAMU a partir de PDFs de escala.

## Arquitetura

- **Frontend:** HTML puro + CSS + JavaScript vanilla
- **Backend:** FastAPI + Python
- **Extração:** pdfplumber + rapidfuzz (fuzzy matching)

## Como usar localmente

```bash
pip install -r requirements.txt
python backend.py
```

Acesse `http://localhost:8000`

## Deploy

Faça deploy no Render.com:

1. Conecte seu repositório GitHub
2. Crie um novo Web Service
3. Use `python backend.py` como comando de start
4. Deploy automático a cada push

## Endpoints

- `GET /` - Retorna index.html
- `POST /processar` - Recebe PDF + nome, retorna top 3 matches
- `POST /confirmar` - Confirma profissional, retorna plantões
- `POST /exportar-json` - Exporta plantões como JSON
- `POST /exportar-csv` - Exporta plantões como CSV
