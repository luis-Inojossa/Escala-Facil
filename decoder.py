"""
decoder.py — Interpreta os códigos de plantão do SAMU.

TIPO A — Profissional fixo (código simples):
  D = diurno (horário vem do cabeçalho da seção)
  N = noturno (horário vem do cabeçalho da seção)
  F = folga
  DH = dia de hora
  Célula vazia = não trabalha

TIPO B — Folguista (código composto):
  Exemplos: DN18, DN19, CB18, VV18, PS6, SU7, B25
  Últimos dígitos = horário, prefixo = local
"""

import re

# Mapeamento de prefixo de local
LOCAL_MAP = {
    "DN": "Distrito Norte",
    "CB": "Castelo Branco",
    "VV": "Vila Virgínia",
    "PS": "Pronto Socorro",
    "SU": "Sumarezinho",
    "BP": "Bonfim Paulista",
    "B25": "Base 25",
    "B27": "Base 27",
    "B11": "Base 11",
    "B": "Base",
}

# Mapeamento de sufixo de horário
HORARIO_MAP = {
    "18": {"inicio": "18:00", "fim": "06:00", "turno": "noturno", "vira_meia_noite": True},
    "19": {"inicio": "19:00", "fim": "07:00", "turno": "noturno", "vira_meia_noite": True},
    "6":  {"inicio": "06:00", "fim": "18:00", "turno": "diurno",  "vira_meia_noite": False},
    "7":  {"inicio": "07:00", "fim": "19:00", "turno": "diurno",  "vira_meia_noite": False},
}

# Cabeçalhos de seção de turno
SECAO_HORARIO_MAP = {
    "DIURNO 06:00 AS 18:00":  {"inicio": "06:00", "fim": "18:00", "turno": "diurno",  "vira_meia_noite": False},
    "DIURNO 07:00 AS 19:00":  {"inicio": "07:00", "fim": "19:00", "turno": "diurno",  "vira_meia_noite": False},
    "NOTURNO 18:00 AS 06:00": {"inicio": "18:00", "fim": "06:00", "turno": "noturno", "vira_meia_noite": True},
    "NOTURNO 19:00 AS 07:00": {"inicio": "19:00", "fim": "07:00", "turno": "noturno", "vira_meia_noite": True},
}


def detectar_tipo(codigo: str) -> str:
    """Detecta se o código é Tipo A (simples) ou Tipo B (composto)."""
    if not codigo:
        return "vazio"
    codigo = codigo.strip().upper()
    # Tipo A: apenas letras sem dígitos, ou DH
    if re.match(r'^[A-Z]+$', codigo) and codigo in ("D", "N", "F", "DH", "FE", "FA"):
        return "A"
    # Tipo B: letras + dígitos
    if re.search(r'\d', codigo):
        return "B"
    # Código não reconhecido mas não vazio
    return "desconhecido"


def decode_tipo_b(codigo: str) -> dict:
    """
    Decodifica um código composto (Tipo B).
    Retorna dict com local, inicio, fim, turno, vira_meia_noite.
    """
    codigo = codigo.strip().upper()

    # Tenta extrair sufixo numérico
    match = re.match(r'^([A-Z]+)(\d+)$', codigo)
    if not match:
        return {
            "local": codigo,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": False,
        }

    prefixo = match.group(1)
    sufixo = match.group(2)

    # Resolve local
    local = LOCAL_MAP.get(prefixo, prefixo)

    # Tenta B25, B27, B11 (prefixo B + número de base)
    if prefixo == "B" and sufixo in ("25", "27", "11"):
        local = f"Base {sufixo}"
        # Sem horário embutido neste caso
        return {
            "local": local,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": True,
        }

    # Resolve horário
    horario = HORARIO_MAP.get(sufixo)
    if not horario:
        return {
            "local": local,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": False,
        }

    return {
        "local": local,
        "inicio": horario["inicio"],
        "fim": horario["fim"],
        "turno": horario["turno"],
        "vira_meia_noite": horario["vira_meia_noite"],
        "codigo_original": codigo,
        "reconhecido": True,
    }


def decode_tipo_a(codigo: str, secao_horario: str) -> dict:
    """
    Decodifica um código simples (Tipo A).
    O horário vem do cabeçalho da seção.
    """
    codigo = codigo.strip().upper()
    horario_secao = SECAO_HORARIO_MAP.get(secao_horario, {})

    if codigo == "F":
        return {
            "tipo": "folga",
            "local": None,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": True,
        }
    elif codigo == "FE":
        return {
            "tipo": "folga_extra",
            "local": None,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": True,
        }
    elif codigo == "FA":
        return {
            "tipo": "falta",
            "local": None,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": True,
        }
    elif codigo == "DH":
        return {
            "tipo": "dia_de_hora",
            "local": None,
            "inicio": horario_secao.get("inicio"),
            "fim": horario_secao.get("fim"),
            "turno": horario_secao.get("turno"),
            "vira_meia_noite": horario_secao.get("vira_meia_noite"),
            "codigo_original": codigo,
            "reconhecido": True,
        }
    elif codigo in ("D", "N"):
        tipo_plantao = "regular"
        return {
            "tipo": tipo_plantao,
            "local": None,
            "inicio": horario_secao.get("inicio"),
            "fim": horario_secao.get("fim"),
            "turno": horario_secao.get("turno"),
            "vira_meia_noite": horario_secao.get("vira_meia_noite"),
            "codigo_original": codigo,
            "reconhecido": True,
        }
    else:
        return {
            "tipo": "desconhecido",
            "local": None,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": False,
        }


def decode_celula(codigo: str, secao_horario: str, is_extra: bool = False) -> dict | None:
    """
    Decodifica uma célula do PDF.
    Retorna None se a célula estiver vazia.
    """
    if not codigo or not codigo.strip():
        return None

    codigo = codigo.strip().upper()
    tipo_codigo = detectar_tipo(codigo)

    if tipo_codigo == "vazio":
        return None

    if tipo_codigo == "A":
        resultado = decode_tipo_a(codigo, secao_horario)
    elif tipo_codigo == "B":
        resultado = decode_tipo_b(codigo)
        resultado["tipo"] = "extra" if is_extra else "regular"
    else:
        # Código não reconhecido — preservar para não descartar silenciosamente
        resultado = {
            "tipo": "desconhecido",
            "local": None,
            "inicio": None,
            "fim": None,
            "turno": None,
            "vira_meia_noite": None,
            "codigo_original": codigo,
            "reconhecido": False,
        }

    if is_extra and resultado.get("tipo") not in ("folga", "folga_extra", "falta"):
        resultado["tipo"] = "extra"

    return resultado
