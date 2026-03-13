"""
extrator.py — Extrai tabelas do PDF de escala do SAMU usando pdfplumber.

Estrutura do PDF:
- Múltiplas páginas, cada uma com uma "base" diferente
- Cada página tem seções de turno (DIURNO/NOTURNO)
- Cada seção tem uma tabela onde:
  - Linha de cabeçalho: dias do mês (1, 2, 3... 31)
  - Cada profissional ocupa DUAS linhas consecutivas:
    Linha 1: NOME | cod | D | F | D | N...
    Linha 2: PL. EXTRA | | | D | | CB18...

Retorna uma lista de seções, cada uma com:
{
  "base": "UBDS Central",
  "secao": "DIURNO 06:00 AS 18:00",
  "profissionais": [
    {
      "nome": "MARIA SILVA",
      "codigo": "12345",
      "dias": {1: "D", 2: "F", 3: "", ...},
      "extras": {1: "", 2: "DN18", 3: "", ...}
    }
  ]
}
"""

import re
import pdfplumber

# Padrões de cabeçalho de seção de turno
SECAO_PATTERNS = [
    r"DIURNO\s+06:00\s+AS\s+18:00",
    r"DIURNO\s+07:00\s+AS\s+19:00",
    r"NOTURNO\s+18:00\s+AS\s+06:00",
    r"NOTURNO\s+19:00\s+AS\s+07:00",
]

def normalizar_secao(texto: str) -> str:
    """Normaliza o texto de cabeçalho de seção."""
    texto = re.sub(r'\s+', ' ', texto.strip().upper())
    for pattern in SECAO_PATTERNS:
        if re.search(pattern, texto):
            match = re.search(pattern, texto)
            return match.group(0).replace(r'\s+', ' ')
    return texto

def is_linha_cabecalho_dias(row: list) -> bool:
    """Verifica se uma linha é o cabeçalho de dias (1..31)."""
    if not row:
        return False
    # Conta quantas células são números de 1 a 31
    numeros = 0
    for cell in row:
        if cell and str(cell).strip().isdigit():
            val = int(str(cell).strip())
            if 1 <= val <= 31:
                numeros += 1
    return numeros >= 10  # pelo menos 10 dias para ser cabeçalho

def is_linha_pl_extra(row: list) -> bool:
    """Verifica se uma linha é a linha PL. EXTRA."""
    if not row:
        return False
    # Procurar "PL. EXTRA" ou "PL EXTRA" nas primeiras 3 colunas
    for i in range(min(3, len(row))):
        celula = str(row[i]).strip().upper() if row[i] else ""
        if "PL" in celula and ("EXTRA" in celula or "EX" in celula):
            return True
    return False

def extrair_mapa_dias(row: list) -> dict:
    """
    Extrai o mapeamento posição_coluna → número_do_dia a partir da linha de cabeçalho.
    Retorna: {indice_coluna: numero_dia}
    """
    mapa = {}
    for i, cell in enumerate(row):
        if cell and str(cell).strip().isdigit():
            val = int(str(cell).strip())
            if 1 <= val <= 31:
                mapa[i] = val
    return mapa

def extrair_nome_e_codigo(row: list) -> tuple[str, str]:
    """
    Extrai nome e código funcional da primeira célula(s) da linha do profissional.
    Retorna: (nome, codigo)
    """
    if not row:
        return ("", "")

    nome = str(row[0]).strip() if row[0] else ""
    codigo = str(row[1]).strip() if len(row) > 1 and row[1] else ""

    # Limpar nome
    nome = re.sub(r'\s+', ' ', nome).upper()

    return (nome, codigo)

def extrair_plantoes_da_linha(row: list, mapa_dias: dict) -> dict:
    """
    Extrai os plantões de uma linha usando o mapeamento de posição.
    Retorna: {numero_dia: codigo_celula}
    """
    plantoes = {}
    for col_idx, dia in mapa_dias.items():
        if col_idx < len(row):
            valor = row[col_idx]
            plantoes[dia] = str(valor).strip() if valor else ""
        else:
            plantoes[dia] = ""
    return plantoes

def extrair_base_da_pagina(page) -> str:
    """Tenta extrair o nome da base a partir do texto da página."""
    texto = page.extract_text() or ""
    linhas = texto.split('\n')

    # Bases conhecidas
    bases_conhecidas = [
        "FOLGUISTAS", "UBDS", "UBS", "PRONTO SOCORRO",
        "VILA VIRGÍNIA", "CASTELO BRANCO", "DISTRITO NORTE",
        "SUMAREZINHO", "BONFIM PAULISTA", "CENTRAL"
    ]

    for linha in linhas[:10]:  # Verifica as primeiras 10 linhas
        linha_upper = linha.strip().upper()
        for base in bases_conhecidas:
            if base in linha_upper:
                return linha.strip()

    # Retorna a primeira linha não vazia como nome da base
    for linha in linhas[:5]:
        if linha.strip():
            return linha.strip()

    return f"Página {page.page_number}"

def extrair_secao_atual(page, y_pos: float) -> str:
    """Tenta identificar a seção de turno mais próxima acima de y_pos."""
    texto = page.extract_text() or ""
    linhas = texto.split('\n')

    secao_atual = ""
    for linha in linhas:
        linha_upper = re.sub(r'\s+', ' ', linha.strip().upper())
        for pattern in SECAO_PATTERNS:
            if re.search(pattern, linha_upper):
                secao_atual = linha_upper
                break

    return secao_atual

def extrair_pdf(caminho_pdf: str) -> list[dict]:
    """
    Extrai todos os dados de escala do PDF.
    Retorna lista de seções com profissionais e plantões.
    """
    resultado = []

    with pdfplumber.open(caminho_pdf) as pdf:
        for page_num, page in enumerate(pdf.pages):
            base = extrair_base_da_pagina(page)
            secao_atual = ""

            # Extrair texto para identificar seções
            texto_pagina = page.extract_text() or ""
            linhas_texto = texto_pagina.split('\n')

            # Identificar seções de turno no texto da página
            secoes_na_pagina = []
            for linha in linhas_texto:
                linha_upper = re.sub(r'\s+', ' ', linha.strip().upper())
                for pattern in SECAO_PATTERNS:
                    if re.search(pattern, linha_upper):
                        match = re.search(pattern, linha_upper)
                        secoes_na_pagina.append(match.group(0))
                        break

            # Extrair tabelas da página
            tabelas = page.extract_tables()

            secao_idx = 0
            for tabela in tabelas:
                if not tabela:
                    continue

                # Verificar se esta tabela tem linha de cabeçalho de dias
                mapa_dias = {}
                cabecalho_encontrado = False
                profissionais_tabela = []

                i = 0
                while i < len(tabela):
                    row = tabela[i]

                    # Verificar se é linha de cabeçalho de dias
                    if is_linha_cabecalho_dias(row):
                        mapa_dias = extrair_mapa_dias(row)
                        cabecalho_encontrado = True
                        # Atualizar seção atual
                        if secao_idx < len(secoes_na_pagina):
                            secao_atual = secoes_na_pagina[secao_idx]
                            secao_idx += 1
                        i += 1
                        continue

                    if not cabecalho_encontrado:
                        i += 1
                        continue

                    # Verificar se é linha PL. EXTRA (segunda linha do profissional)
                    if is_linha_pl_extra(row):
                        # Associar ao último profissional adicionado APENAS se ainda não tem extras
                        if profissionais_tabela and not profissionais_tabela[-1]["extras"]:
                            extras = extrair_plantoes_da_linha(row, mapa_dias)
                            # Só associar se encontrou algo
                            if any(extras.values()):
                                profissionais_tabela[-1]["extras"] = extras
                        i += 1
                        continue

                    # Verificar se é linha de profissional (tem nome na primeira coluna)
                    primeira_celula = str(row[0]).strip() if row[0] else ""
                    if primeira_celula and len(primeira_celula) > 2 and not primeira_celula.isdigit():
                        # Verificar se não é um cabeçalho de seção
                        primeira_upper = primeira_celula.upper()
                        is_secao = any(re.search(p, primeira_upper) for p in SECAO_PATTERNS)
                        is_cabecalho = any(kw in primeira_upper for kw in [
                            "NOME", "PROFISSIONAL", "FUNCIONÁRIO", "TOTAL"
                        ])

                        if not is_secao and not is_cabecalho:
                            nome, codigo = extrair_nome_e_codigo(row)
                            if nome and len(nome) > 2:
                                dias = extrair_plantoes_da_linha(row, mapa_dias)
                                profissionais_tabela.append({
                                    "nome": nome,
                                    "codigo": codigo,
                                    "dias": dias,
                                    "extras": {},
                                })

                    i += 1

                if profissionais_tabela:
                    resultado.append({
                        "base": base,
                        "secao": secao_atual,
                        "pagina": page_num + 1,
                        "profissionais": profissionais_tabela,
                    })

    return resultado

def extrair_todos_nomes(caminho_pdf: str) -> list[dict]:
    """
    Extrai todos os nomes de profissionais do PDF para busca fuzzy.
    Retorna lista de {nome, codigo, base, secao}.
    """
    secoes = extrair_pdf(caminho_pdf)
    nomes = []
    vistos = set()

    for secao in secoes:
        for prof in secao["profissionais"]:
            nome = prof["nome"]
            if nome and nome not in vistos:
                vistos.add(nome)
                nomes.append({
                    "nome": nome,
                    "codigo": prof.get("codigo", ""),
                    "base": secao["base"],
                    "secao": secao["secao"],
                })

    return nomes
