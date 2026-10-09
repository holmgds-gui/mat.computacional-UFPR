"""Converte uma Issue dos formulários "Nova avaliação" / "Nova atividade" em uma linha de dados/.

Executado pelo workflow .github/workflows/formularios.yml. Lê o corpo da Issue da variável de
ambiente ISSUE_BODY e o tipo de formulário de FORMULARIO (avaliacao | atividade).
Imprime a mensagem de resposta; sai com código 1 se os dados forem inválidos.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys

from comum import DADOS, ler_yaml

SEM_RESPOSTA = {"", "_no response_", "none"}


def campos(corpo: str) -> dict[str, str]:
    partes = re.split(r"^###\s+(.+?)\s*$", corpo, flags=re.M)
    return {partes[i].strip(): partes[i + 1].strip() for i in range(1, len(partes) - 1, 2)}


def valor(c: dict, rotulo_inicio: str) -> str:
    for k, v in c.items():
        if k.startswith(rotulo_inicio):
            return "" if v.casefold() in SEM_RESPOSTA else v
    return ""


def data_valida(texto: str) -> str:
    return dt.date.fromisoformat(texto.strip()).isoformat()


def anexar(arquivo, chave: str, item: dict) -> None:
    texto = arquivo.read_text(encoding="utf-8")
    texto = re.sub(rf"^{chave}:\s*\[\]\s*$", f"{chave}:", texto, flags=re.M)
    linha = "  - " + json.dumps(item, ensure_ascii=False)  # JSON é YAML válido
    arquivo.write_text(texto.rstrip("\n") + "\n" + linha + "\n", encoding="utf-8")
    ler_yaml(arquivo)  # garante que o arquivo continua válido


def avaliacao(c: dict) -> str:
    codigo = valor(c, "Disciplina").upper().replace(" ", "")
    if not re.fullmatch(r"[A-Z]{2,4}\d{3,4}[A-Z]?", codigo):
        raise ValueError(f"código de disciplina inválido: {codigo!r}")
    item = {"codigo": codigo, "titulo": valor(c, "Título")[:120], "data": data_valida(valor(c, "Data")),
            "tipo": valor(c, "Tipo") or "prova"}
    if hora := valor(c, "Hora"):
        dt.time.fromisoformat(hora)
        item["hora"] = hora
    if alerta := valor(c, "Avisar"):
        item["alerta"] = int(alerta)
    if obs := valor(c, "Observações"):
        item["obs"] = obs[:500]
    anexar(DADOS / "avaliacoes.yml", "avaliacoes", item)
    return f"✅ Cadastrado: **{codigo} — {item['titulo']}** em {item['data']}. Já entra no calendário e no painel."


def atividade(c: dict) -> str:
    conta = valor(c, "Conta como")
    cat = valor(c, "Categoria")
    if (conta == "extensao") != cat.startswith("ACE-"):
        raise ValueError("categoria não combina com 'conta como' (extensão usa ACE-I…V; formativa usa as minúsculas)")
    item = {"titulo": valor(c, "Atividade")[:150], "data": data_valida(valor(c, "Data")),
            "horas": float(valor(c, "Horas").replace(",", ".")), "conta_como": conta, "categoria": cat,
            "certificado": "[x]" in valor(c, "Comprovante").lower()}
    if obs := valor(c, "Observações"):
        item["obs"] = obs[:500]
    anexar(DADOS / "atividades.yml", "atividades", item)
    return f"✅ Registrado: **{item['titulo']}**: {item['horas']:g}h como {conta} ({cat})."


def main() -> None:
    c = campos(os.environ["ISSUE_BODY"])
    try:
        msg = {"avaliacao": avaliacao, "atividade": atividade}[os.environ["FORMULARIO"]](c)
    except (ValueError, KeyError) as e:
        print(f"❌ Não consegui registrar: {e}. Edite a Issue e reabra, ou corrija direto em `dados/`.")
        sys.exit(1)
    print(msg)


if __name__ == "__main__":
    main()
