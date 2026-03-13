#!/usr/bin/env python3
"""
cli.py — Interface de linha de comando para o pipeline de extração de PDF.

Uso:
  python3 cli.py processar <caminho_pdf> <nome_query>
    → Retorna JSON com top 3 matches e session_id

  python3 cli.py confirmar <caminho_pdf> <nome_escolhido> [mes] [ano]
    → Retorna JSON com plantões estruturados

Saída: JSON para stdout, erros para stderr
"""

import sys
import json
import os
import re

# Adicionar o diretório pai ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_pipeline.extrator import extrair_pdf, extrair_todos_nomes
from pdf_pipeline.mapeador import encontrar_e_mapear_profissional, extrair_mes_ano_do_pdf
from fuzzy_match import buscar_top3


def cmd_processar(caminho_pdf: str, nome_query: str):
    """Processa o PDF e retorna os top 3 matches."""
    try:
        print(f"[PYTHON] Iniciando cmd_processar", file=sys.stderr)
        print(f"[PYTHON] Arquivo: {caminho_pdf}", file=sys.stderr)
        print(f"[PYTHON] Nome query: {nome_query}", file=sys.stderr)
        
        # Extrair todos os nomes do PDF
        print(f"[PYTHON] Extraindo nomes do PDF...", file=sys.stderr)
        lista_nomes = extrair_todos_nomes(caminho_pdf)
        print(f"[PYTHON] Total de nomes extraídos: {len(lista_nomes)}", file=sys.stderr)

        if not lista_nomes:
            print(json.dumps({
                "error": "Nenhum profissional encontrado no PDF. Verifique se o arquivo é uma escala do SAMU.",
                "matches": []
            }))
            return

        # Buscar top 3 matches
        print(f"[PYTHON] Buscando top 3 matches para '{nome_query}'...", file=sys.stderr)
        top3 = buscar_top3(nome_query, lista_nomes)
        print(f"[PYTHON] Top 3 matches encontrados: {len(top3)}", file=sys.stderr)

        if not top3:
            print(json.dumps({
                "error": f"Nenhum profissional similar a '{nome_query}' encontrado.",
                "matches": []
            }))
            return

        print(f"[PYTHON] Retornando resultado com sucesso", file=sys.stderr)
        print(json.dumps({
            "matches": top3,
            "total_profissionais": len(lista_nomes),
        }))

    except Exception as e:
        import traceback
        print(f"[PYTHON ERROR] {str(e)}", file=sys.stderr)
        print(f"[PYTHON ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
        print(json.dumps({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "matches": []
        }))


def cmd_confirmar(caminho_pdf: str, nome_escolhido: str, mes: int = 0, ano: int = 0):
    """Confirma o profissional e retorna os plantões estruturados."""
    try:
        print(f"[PYTHON] Iniciando cmd_confirmar", file=sys.stderr)
        print(f"[PYTHON] Arquivo: {caminho_pdf}", file=sys.stderr)
        print(f"[PYTHON] Nome escolhido: {nome_escolhido}, Mês: {mes}, Ano: {ano}", file=sys.stderr)
        
        # Extrair todas as seções do PDF
        print(f"[PYTHON] Extraindo seções do PDF...", file=sys.stderr)
        secoes = extrair_pdf(caminho_pdf)
        print(f"[PYTHON] Seções extraídas: {len(secoes)}", file=sys.stderr)

        if not secoes:
            print(json.dumps({
                "error": "Não foi possível extrair dados do PDF.",
            }))
            return

        # Detectar mês e ano se não fornecidos
        if mes == 0 or ano == 0:
            mes_det, ano_det = extrair_mes_ano_do_pdf(secoes)
            if mes == 0:
                mes = mes_det
            if ano == 0:
                ano = ano_det

        # Mapear plantões do profissional
        print(f"[PYTHON] Mapeando plantões do profissional...", file=sys.stderr)
        resultado = encontrar_e_mapear_profissional(secoes, nome_escolhido, mes, ano)
        print(f"[PYTHON] Plantões mapeados com sucesso", file=sys.stderr)

        if resultado is None:
            print(json.dumps({
                "error": f"Profissional '{nome_escolhido}' não encontrado no PDF.",
            }))
            return

        print(f"[PYTHON] Retornando resultado com sucesso", file=sys.stderr)
        print(json.dumps(resultado, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(f"[PYTHON ERROR] {str(e)}", file=sys.stderr)
        print(f"[PYTHON ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
        print(json.dumps({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }))


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Uso: cli.py <comando> <args...>"}))
        sys.exit(1)

    comando = sys.argv[1]
    caminho_pdf = sys.argv[2]

    if not os.path.exists(caminho_pdf):
        print(json.dumps({"error": f"Arquivo não encontrado: {caminho_pdf}"}))
        sys.exit(1)

    if comando == "processar":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Uso: cli.py processar <pdf> <nome>"}))
            sys.exit(1)
        nome_query = sys.argv[3]
        cmd_processar(caminho_pdf, nome_query)

    elif comando == "confirmar":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Uso: cli.py confirmar <pdf> <nome> [mes] [ano]"}))
            sys.exit(1)
        nome_escolhido = sys.argv[3]
        mes = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        ano = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        cmd_confirmar(caminho_pdf, nome_escolhido, mes, ano)

    else:
        print(json.dumps({"error": f"Comando desconhecido: {comando}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
