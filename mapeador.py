"""
mapeador.py — Converte células extraídas do PDF em plantões estruturados.

Recebe os dados brutos do extrator e produz o JSON de saída esperado:
{
  "profissional": "...",
  "codigo_funcional": "...",
  "base": "...",
  "mes": 3,
  "ano": 2026,
  "plantoes": [...],
  "extras": [...],
  "folgas": [...],
  "total_plantoes": N,
  "total_horas": N
}
"""

import re
from datetime import date, timedelta
from .decoder import decode_celula, SECAO_HORARIO_MAP

DIAS_SEMANA = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}

def extrair_mes_ano_do_pdf(secoes: list) -> tuple[int, int]:
    """
    Tenta extrair mês e ano do PDF a partir dos dados disponíveis.
    Retorna (mes, ano) ou (0, 0) se não encontrado.
    """
    # Tenta encontrar no texto das bases
    for secao in secoes:
        base = secao.get("base", "")
        match = re.search(r'(\d{1,2})[/\-](\d{4})', base)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r'(\d{4})', base)
        if match:
            ano = int(match.group(1))
            if 2020 <= ano <= 2030:
                return 0, ano

    return 0, 0

def calcular_horas(inicio: str, fim: str, vira_meia_noite: bool) -> float:
    """Calcula a duração em horas de um plantão."""
    if not inicio or not fim:
        return 12.0  # padrão

    try:
        h_ini, m_ini = map(int, inicio.split(":"))
        h_fim, m_fim = map(int, fim.split(":"))

        minutos_ini = h_ini * 60 + m_ini
        minutos_fim = h_fim * 60 + m_fim

        if vira_meia_noite or minutos_fim <= minutos_ini:
            minutos_fim += 24 * 60

        return (minutos_fim - minutos_ini) / 60.0
    except Exception:
        return 12.0

def montar_data(dia: int, mes: int, ano: int) -> str:
    """Monta string de data no formato YYYY-MM-DD."""
    if mes == 0 or ano == 0:
        return f"????-??-{dia:02d}"
    try:
        d = date(ano, mes, dia)
        return d.isoformat()
    except ValueError:
        return f"{ano}-{mes:02d}-{dia:02d}"

def dia_semana_str(dia: int, mes: int, ano: int) -> str:
    """Retorna o nome do dia da semana."""
    if mes == 0 or ano == 0:
        return "?"
    try:
        d = date(ano, mes, dia)
        return DIAS_SEMANA[d.weekday()]
    except ValueError:
        return "?"

def mapear_profissional(
    prof_data: dict,
    secao: str,
    base: str,
    mes: int,
    ano: int,
) -> dict:
    """
    Mapeia os dados brutos de um profissional para o formato de saída.
    """
    nome = prof_data.get("nome", "")
    codigo = prof_data.get("codigo", "")
    dias_raw = prof_data.get("dias", {})
    extras_raw = prof_data.get("extras", {})

    plantoes = []
    extras = []
    folgas = []
    total_horas = 0.0

    # Processar dias regulares
    for dia, codigo_celula in sorted(dias_raw.items(), key=lambda x: x[0]):
        if not codigo_celula or not codigo_celula.strip():
            continue

        decoded = decode_celula(codigo_celula, secao, is_extra=False)
        if decoded is None:
            continue

        tipo = decoded.get("tipo", "desconhecido")
        data_str = montar_data(dia, mes, ano)
        dia_semana = dia_semana_str(dia, mes, ano)

        if tipo == "folga":
            folgas.append(dia)
        elif tipo in ("regular", "dia_de_hora", "desconhecido"):
            horas = calcular_horas(
                decoded.get("inicio"),
                decoded.get("fim"),
                decoded.get("vira_meia_noite", False),
            )
            total_horas += horas
            plantoes.append({
                "dia": dia,
                "data": data_str,
                "dia_semana": dia_semana,
                "tipo": tipo,
                "local": decoded.get("local") or base,
                "inicio": decoded.get("inicio"),
                "fim": decoded.get("fim"),
                "vira_meia_noite": decoded.get("vira_meia_noite", False),
                "codigo_original": decoded.get("codigo_original", codigo_celula),
            })

    # Processar extras (segunda linha — PL. EXTRA)
    for dia, codigo_celula in sorted(extras_raw.items(), key=lambda x: x[0]):
        if not codigo_celula or not codigo_celula.strip():
            continue

        decoded = decode_celula(codigo_celula, secao, is_extra=True)
        if decoded is None:
            continue

        tipo = decoded.get("tipo", "extra")
        data_str = montar_data(dia, mes, ano)
        dia_semana = dia_semana_str(dia, mes, ano)

        if tipo == "folga":
            pass  # folga extra — ignorar ou registrar separadamente
        else:
            horas = calcular_horas(
                decoded.get("inicio"),
                decoded.get("fim"),
                decoded.get("vira_meia_noite", False),
            )
            total_horas += horas
            extras.append({
                "dia": dia,
                "data": data_str,
                "dia_semana": dia_semana,
                "tipo": "extra",
                "local": decoded.get("local") or base,
                "inicio": decoded.get("inicio"),
                "fim": decoded.get("fim"),
                "vira_meia_noite": decoded.get("vira_meia_noite", False),
                "codigo_original": decoded.get("codigo_original", codigo_celula),
            })

    total_plantoes = len(plantoes) + len(extras)

    return {
        "profissional": nome,
        "codigo_funcional": codigo,
        "base": base,
        "secao": secao,
        "mes": mes,
        "ano": ano,
        "plantoes": plantoes,
        "extras": extras,
        "folgas": folgas,
        "total_plantoes": total_plantoes,
        "total_horas": round(total_horas, 1),
    }

def encontrar_e_mapear_profissional(
    secoes: list,
    nome_escolhido: str,
    mes: int = 0,
    ano: int = 0,
) -> dict | None:
    """
    Encontra o profissional pelo nome exato nas seções extraídas e mapeia seus plantões.
    """
    if mes == 0 or ano == 0:
        mes_detectado, ano_detectado = extrair_mes_ano_do_pdf(secoes)
        if mes == 0:
            mes = mes_detectado
        if ano == 0:
            ano = ano_detectado

    for secao_data in secoes:
        for prof in secao_data.get("profissionais", []):
            if prof["nome"].upper() == nome_escolhido.upper():
                return mapear_profissional(
                    prof,
                    secao_data.get("secao", ""),
                    secao_data.get("base", ""),
                    mes,
                    ano,
                )

    return None
