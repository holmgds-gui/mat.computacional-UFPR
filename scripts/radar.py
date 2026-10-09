"""Radar: verifica os sites da UFPR listados em dados/fontes.yml e abre Issues com novidades.

- Na primeira vez que vê uma fonte, só memoriza o estado (não abre Issues de coisas antigas).
- O estado fica em dados/estado/radar.json; o histórico recente em dados/estado/radar-log.json.

Uso:
  python scripts/radar.py             # roda de verdade (no GitHub Actions abre Issues)
  python scripts/radar.py --simular   # só mostra o que encontraria, sem salvar nada
"""

from __future__ import annotations

import hashlib
import html
import re
import sys

from comum import ESTADO, DADOS, GitHub, baixar, baixar_json, hoje, ler_json, ler_yaml, normalizar, salvar_json

ARQ_ESTADO = ESTADO / "radar.json"
ARQ_LOG = ESTADO / "radar-log.json"
MAX_IDS = 300
MAX_ISSUES_SEPARADAS = 3  # acima disso, agrupa as novidades da fonte numa Issue só


def texto_html(bruto: str) -> str:
    bruto = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", bruto)
    m = re.search(r"(?is)<main\b.*?</main>", bruto) or re.search(r"(?is)<body\b.*?</body>", bruto)
    if m:
        bruto = m.group(0)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", bruto))).strip()


def _tem(alvo: str, palavras) -> bool:
    return any(re.search(rf"\b{re.escape(normalizar(p))}\b", alvo) for p in palavras or [])


def casa(texto: str, filtro, excluir=None) -> bool:
    alvo = normalizar(texto)
    if _tem(alvo, excluir):
        return False
    return filtro in (None, "todos") or _tem(alvo, filtro)


def wp_posts(fonte: dict, estado: dict, simular: bool) -> list[dict]:
    posts = baixar_json(f"{fonte['url'].rstrip('/')}/wp-json/wp/v2/posts?per_page=20&_fields=id,date,link,title,excerpt")
    vistos = set(estado.get("vistos", []))
    primeira_vez = "vistos" not in estado
    novos = []
    for p in posts:
        titulo = html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip()
        resumo = texto_html(p.get("excerpt", {}).get("rendered", ""))[:400]
        item = {"titulo": titulo, "link": p["link"], "data": p["date"][:10], "resumo": resumo}
        if simular:
            if casa(titulo + " " + resumo, fonte.get("filtro"), fonte.get("excluir")):
                novos.append(item)
            continue
        if p["id"] in vistos:
            continue
        vistos.add(p["id"])
        if not primeira_vez and casa(titulo + " " + resumo, fonte.get("filtro"), fonte.get("excluir")):
            novos.append(item)
    if not simular:
        estado["vistos"] = sorted(vistos)[-MAX_IDS:]
    return novos


def wp_pages(fonte: dict, estado: dict, simular: bool) -> list[dict]:
    # Só as 15 páginas modificadas mais recentemente: consulta leve (o servidor do curso é lento)
    paginas = baixar_json(f"{fonte['url'].rstrip('/')}/wp-json/wp/v2/pages"
                          "?per_page=15&orderby=modified&order=desc&_fields=id,modified,link,title")
    antes = estado.get("modificadas")
    agora, novos = dict(antes or {}), []
    for p in paginas:
        agora[str(p["id"])] = p["modified"]
        titulo = html.unescape(p["title"]["rendered"]).strip()
        if antes is not None and antes.get(str(p["id"])) != p["modified"]:
            novos.append({"titulo": f"Página atualizada: {titulo}", "link": p["link"], "data": p["modified"][:10], "resumo": ""})
    if simular:
        return [{"titulo": f"(monitorando) {t['title']['rendered']} — {t['modified'][:10]}", "link": t["link"],
                 "data": "", "resumo": ""} for t in paginas]
    estado["modificadas"] = agora
    return novos


def pagina(fonte: dict, estado: dict, simular: bool) -> list[dict]:
    corpo, charset = baixar(fonte["url"])
    try:
        texto = corpo.decode(charset or "utf-8")
    except UnicodeDecodeError:
        texto = corpo.decode("latin-1")
    resumo = hashlib.sha256(texto_html(texto).encode()).hexdigest()
    anterior = estado.get("hash")
    if simular:
        return [{"titulo": f"(monitorando) hash {resumo[:10]}", "link": fonte["url"], "data": "", "resumo": ""}]
    estado["hash"] = resumo
    if anterior and anterior != resumo:
        return [{"titulo": f"Página mudou: {fonte['nome']}", "link": fonte.get("link", fonte["url"]),
                 "data": str(hoje()), "resumo": ""}]
    return []


TIPOS = {"wp_posts": wp_posts, "wp_pages": wp_pages, "pagina": pagina}


def corpo_issue(fonte: dict, itens: list[dict]) -> str:
    linhas = [f"Novidade(s) detectada(s) pelo radar em **{fonte['nome']}** ({fonte['url']}).", ""]
    for it in itens:
        linhas.append(f"- [{it['titulo']}]({it['link']})" + (f" — {it['data']}" if it["data"] else ""))
        if it["resumo"]:
            linhas.append(f"  > {it['resumo'][:300]}")
    linhas += ["", "_Feche esta Issue quando tiver lido. Ajuste as fontes em `dados/fontes.yml`._"]
    return "\n".join(linhas)


def main() -> None:
    simular = "--simular" in sys.argv
    config = ler_yaml(DADOS / "fontes.yml")
    estado = ler_json(ARQ_ESTADO, {})
    log = ler_json(ARQ_LOG, [])
    gh = GitHub()
    erros = []

    try:
        for fonte in config["fontes"]:
            st = estado.setdefault(fonte["id"], {})
            try:
                novos = TIPOS[fonte["tipo"]](fonte, st, simular)
            except Exception as e:  # uma fonte fora do ar não derruba as outras
                erros.append(f"{fonte['id']}: {e}")
                print(f"[erro] {fonte['id']}: {e}")
                continue
            print(f"[{fonte['id']}] {len(novos)} item(ns)")
            for it in novos[:8] if simular else []:
                print(f"   - {it['data']} {it['titulo'][:100]}")
            if simular or not novos:
                continue

            rotulos = ["radar", fonte.get("rotulo", "ufpr")]
            if len(novos) <= MAX_ISSUES_SEPARADAS:
                for it in novos:
                    gh.abrir_issue(f"📡 {it['titulo'][:200]}", corpo_issue(fonte, [it]), rotulos)
            else:
                gh.abrir_issue(f"📡 {len(novos)} novidades em {fonte['nome']}", corpo_issue(fonte, novos), rotulos)
            for it in novos:
                log.insert(0, {**it, "fonte": fonte["nome"], "visto_em": str(hoje())})

    finally:  # salva o que já foi visto mesmo se algo falhar no meio
        if not simular:
            salvar_json(ARQ_ESTADO, estado)
            salvar_json(ARQ_LOG, log[:40])
    if erros:
        print("Fontes com erro (o radar continua nas próximas execuções):\n  " + "\n  ".join(erros))


if __name__ == "__main__":
    main()
