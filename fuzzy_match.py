"""
fuzzy_match.py — Busca aproximada de nomes usando rapidfuzz.

Passos:
1. Recebe lista de nomes extraídos do PDF
2. Compara com o nome digitado pelo usuário
3. Retorna os top 3 matches com percentual de similaridade
"""

from rapidfuzz import fuzz, process


def buscar_top3(nome_query: str, lista_profissionais: list[dict]) -> list[dict]:
    """
    Busca os top 3 profissionais mais similares ao nome digitado.

    Args:
        nome_query: Nome digitado pelo usuário
        lista_profissionais: Lista de dicts com {nome, codigo, base, secao}

    Returns:
        Lista de até 3 dicts com {nome, codigo, base, secao, score}
    """
    if not lista_profissionais:
        return []

    nome_query = nome_query.strip().upper()

    # Extrair apenas os nomes para o processo de matching
    nomes = [p["nome"] for p in lista_profissionais]

    # Usar token_set_ratio para melhor correspondência parcial
    # (ex: "Luis Augusto" encontra "LUIS AUGUSTO M. DE SOUZA")
    resultados = process.extract(
        nome_query,
        nomes,
        scorer=fuzz.token_set_ratio,
        limit=3,
    )

    top3 = []
    for nome_match, score, idx in resultados:
        if score >= 40:  # Threshold mínimo de 40%
            prof = lista_profissionais[idx].copy()
            prof["score"] = round(score, 1)
            top3.append(prof)

    return top3


def buscar_nome_exato(nome: str, lista_profissionais: list[dict]) -> dict | None:
    """
    Busca um profissional pelo nome exato (case-insensitive).
    """
    nome_upper = nome.strip().upper()
    for prof in lista_profissionais:
        if prof["nome"].upper() == nome_upper:
            return prof
    return None
