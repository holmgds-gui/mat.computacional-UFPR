"""Funções compartilhadas pelos scripts do repositório."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
ESTADO = DADOS / "estado"
SITE = RAIZ / "site"

# Brasil não tem horário de verão desde 2019: UTC-3 fixo.
FUSO = dt.timezone(dt.timedelta(hours=-3), "BRT")
USER_AGENT = "matind-ufpr-repo/1.0 (+https://github.com/holmgds-gui/mat.computacional-UFPR)"


def hoje() -> dt.date:
    return dt.datetime.now(FUSO).date()


def ler_yaml(caminho: Path):
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ler_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def salvar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def como_data(valor) -> dt.date:
    if isinstance(valor, dt.date):
        return valor
    return dt.date.fromisoformat(str(valor))


def normalizar(texto: str) -> str:
    """Remove acentos e caixa para comparar palavras-chave."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.casefold()


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")


def baixar(url: str, timeout: int = 90, tentativas: int = 2) -> tuple[bytes, str]:
    """Baixa uma URL. Os servidores da UFPR às vezes respondem 503/504, então tenta de novo."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for n in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.headers.get_content_charset() or ""
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo = e
            if isinstance(e, urllib.error.HTTPError) and e.code not in (429, 500, 502, 503, 504):
                raise
            if n + 1 < tentativas:
                time.sleep(15)
    raise ultimo


def baixar_json(url: str, timeout: int = 60):
    corpo, charset = baixar(url, timeout)
    return json.loads(corpo.decode(charset or "utf-8"))


def eventos_do_calendario() -> list[dict]:
    """Junta todos os dados/calendario-*.yml em uma lista de eventos de dia inteiro."""
    eventos = []
    for arq in sorted(DADOS.glob("calendario-*.yml")):
        for ev in ler_yaml(arq).get("eventos") or []:
            ev = dict(ev)
            ev["inicio"] = como_data(ev["inicio"])
            ev["fim"] = como_data(ev.get("fim") or ev["inicio"])
            eventos.append(ev)
    return eventos


def avaliacoes() -> list[dict]:
    itens = []
    for av in ler_yaml(DADOS / "avaliacoes.yml").get("avaliacoes") or []:
        av = dict(av)
        av["data"] = como_data(av["data"])
        itens.append(av)
    return itens


# ---------------------------------------------------------------- GitHub


class GitHub:
    """Cliente mínimo da API do GitHub. Sem GITHUB_TOKEN, só imprime o que faria."""

    CORES = {
        "radar": "0e8a16", "prazo": "d93f0b", "avaliacao": "b60205", "ic": "5319e7",
        "extensao": "1d76db", "evento": "fbca04", "curso": "006b75", "graduacao": "c5def5",
        "setor": "bfdadc", "ufpr": "ededed", "lembrete": "e99695",
    }

    def __init__(self) -> None:
        self.token = os.environ.get("GITHUB_TOKEN")
        self.repo = os.environ.get("GITHUB_REPOSITORY")
        self.ativo = bool(self.token and self.repo)
        self._rotulos_ok: set[str] = set()

    def _chamar(self, metodo: str, caminho: str, corpo: dict | None = None):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo}{caminho}",
            data=json.dumps(corpo).encode() if corpo is not None else None,
            method=metodo,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"null")

    def _garantir_rotulo(self, nome: str) -> None:
        if nome in self._rotulos_ok:
            return
        try:
            self._chamar("POST", "/labels", {"name": nome, "color": self.CORES.get(nome, "cccccc")})
        except urllib.error.HTTPError as e:
            if e.code != 422:  # 422 = já existe
                raise
        self._rotulos_ok.add(nome)

    def abrir_issue(self, titulo: str, corpo: str, rotulos: list[str]) -> None:
        if not self.ativo:
            print(f"  [simulação] Issue: {titulo}  {rotulos}")
            return
        for r in rotulos:
            self._garantir_rotulo(r)
        resp = self._chamar("POST", "/issues", {"title": titulo, "body": corpo, "labels": rotulos})
        print(f"  Issue aberta: #{resp['number']} {titulo}")
