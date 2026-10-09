"""Atualiza o painel do README.md e abre Issues de lembrete para prazos e provas.

O painel fica entre os marcadores <!-- painel:inicio --> e <!-- painel:fim -->.
Lembretes: eventos com `alerta: N` (calendário) e todas as avaliações (padrão 7 dias)
geram uma Issue uma única vez, N dias antes. Controle em dados/estado/alertas.json.

Uso: python scripts/painel.py
"""

from __future__ import annotations

import datetime as dt
import re

from comum import DADOS, ESTADO, RAIZ, GitHub, avaliacoes, como_data, eventos_do_calendario, hoje, ler_json, ler_yaml, salvar_json

README = RAIZ / "README.md"
ARQ_ALERTAS = ESTADO / "alertas.json"
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
NOME_DIA = {"seg": "segunda", "ter": "terça", "qua": "quarta", "qui": "quinta", "sex": "sexta", "sab": "sábado", "dom": "domingo"}


def barra(feito: float, total: float, largura: int = 20) -> str:
    frac = 0 if total == 0 else min(feito / total, 1)
    cheio = round(frac * largura)
    return "█" * cheio + "░" * (largura - cheio) + f" {feito:g}/{total:g}h ({frac:.0%})"


def quando(inicio: dt.date, fim: dt.date, h: dt.date) -> str:
    if inicio <= h <= fim:
        resta = (fim - h).days
        return "**em andamento** — " + ("termina hoje" if resta == 0 else f"termina em {resta} dia(s) ({fim:%d/%m})")
    falta = (inicio - h).days
    return "amanhã" if falta == 1 else f"em {falta} dias"


def secao_hoje(h: dt.date) -> list[str]:
    curso = ler_yaml(DADOS / "curso.yml")
    linhas = [f"**Hoje:** {h:%d/%m/%Y} ({NOME_DIA[DIAS_SEMANA[h.weekday()]]}) · semestre {curso['semestre_atual']} · {curso['periodo_atual']}º período", ""]
    arq = DADOS / f"horario-{curso['semestre_atual']}.yml"
    if not arq.exists():
        return linhas
    horario = ler_yaml(arq)
    sem_aula = {como_data(x) for x in horario.get("sem_aula") or []}
    dentro = como_data(horario["inicio"]) <= h <= como_data(horario["fim"])
    dia = DIAS_SEMANA[h.weekday()]
    aulas = sorted((a for a in horario["aulas"] if dia in a["dias"]), key=lambda a: a["inicio"])
    if dentro and h not in sem_aula and aulas:
        linhas.append("**Aulas de hoje:** " + " · ".join(f"{a['inicio']} {a['codigo']} {a['nome']}" for a in aulas))
    elif h in sem_aula:
        linhas.append("**Hoje não tem aula** (feriado).")
    linhas.append("")
    return linhas


def secao_prazos(h: dt.date) -> list[str]:
    itens = []
    for ev in eventos_do_calendario():
        if ev["fim"] >= h and ev["inicio"] <= h + dt.timedelta(days=30) and ev.get("tipo") != "feriado":
            itens.append((ev["inicio"], ev["fim"], ev["titulo"]))
    for av in avaliacoes():
        if h <= av["data"] <= h + dt.timedelta(days=30):
            itens.append((av["data"], av["data"], f"🧪 {av['codigo']} — {av['titulo']}"))
    itens.sort()
    linhas = ["### ⏳ Próximos 30 dias", ""]
    if not itens:
        return linhas + ["Nada no horizonte. 🌤️", ""]
    linhas += ["| Quando | O quê | Situação |", "|---|---|---|"]
    for ini, fim, titulo in itens:
        datas = f"{ini:%d/%m}" + (f"–{fim:%d/%m}" if fim != ini else "")
        linhas.append(f"| {datas} | {titulo} | {quando(ini, fim, h)} |")
    return linhas + [""]


def secao_progresso() -> list[str]:
    curso = ler_yaml(DADOS / "curso.yml")
    ch = curso["carga_horaria"]
    grade = ler_yaml(DADOS / "grade.yml")
    disciplinas = [d for sem in grade["semestres"].values() for d in sem]
    concluidas = sum(d["ch"] for d in disciplinas if d["status"] in ("concluida", "dispensada"))
    cursando = sum(d["ch"] for d in disciplinas if d["status"] == "cursando")
    a_confirmar = [d["codigo"] for d in disciplinas if d["status"] != "pendente" and d.get("confirmado") is False]
    optativas = sum(60 for o in grade.get("optativas_planejadas") or [] if o["status"] == "concluida")

    ativ = ler_yaml(DADOS / "atividades.yml")
    limites = ativ["limites_formativas"]
    por_cat: dict[str, float] = {}
    ext_total = ext_iv = 0.0
    for a in ativ.get("atividades") or []:
        if a["conta_como"] == "formativa":
            por_cat[a["categoria"]] = por_cat.get(a["categoria"], 0) + a["horas"]
        else:
            ext_total += a["horas"]
            ext_iv += a["horas"] if a["categoria"] == "ACE-IV" else 0
    formativas = sum(min(h, limites.get(c, 0)) for c, h in por_cat.items())

    linhas = [
        "### 📊 Integralização",
        "",
        "| Componente | Progresso |",
        "|---|---|",
        f"| Obrigatórias | `{barra(concluidas, ch['obrigatorias'])}` + {cursando}h cursando |",
        f"| Optativas | `{barra(optativas, ch['optativas'])}` |",
        f"| Atividades formativas | `{barra(formativas, ch['formativas'])}` |",
        f"| Extensão (ACE) | `{barra(ext_total, ch['extensao'])}` · ACE IV: {ext_iv:g}/{ch['extensao_ace_iv_minimo']}h |",
        "",
    ]
    if a_confirmar:
        linhas += [f"> ⚠️ Situação a conferir no SIGA: {', '.join(a_confirmar)}. Depois, marque `confirmado: true` em `dados/grade.yml`.", ""]
    return linhas


def secao_radar() -> list[str]:
    log = ler_json(ESTADO / "radar-log.json", [])[:8]
    linhas = ["### 📡 Últimas do radar", ""]
    if not log:
        return linhas + ["_O radar ainda está aprendendo as fontes. As novidades aparecem aqui e nas [Issues](https://github.com/holmgds-gui/mat.computacional-UFPR/issues?q=label%3Aradar)._", ""]
    for it in log:
        linhas.append(f"- {it['visto_em'][8:10]}/{it['visto_em'][5:7]} · [{it['titulo']}]({it['link']}) — _{it['fonte']}_")
    return linhas + [""]


def lembretes(h: dt.date) -> None:
    enviados = ler_json(ARQ_ALERTAS, {})
    gh = GitHub()
    pendentes = []
    for ev in eventos_do_calendario():
        if ev.get("alerta") is not None:
            pendentes.append((f"cal|{ev['titulo']}|{ev['inicio']}", ev["inicio"], ev["fim"], int(ev["alerta"]),
                              ev["titulo"], ev.get("obs", ""), ["lembrete", "prazo"]))
    for av in avaliacoes():
        pendentes.append((f"aval|{av['codigo']}|{av['titulo']}|{av['data']}", av["data"], av["data"], int(av.get("alerta", 7)),
                          f"{av['codigo']} — {av['titulo']}", av.get("obs", ""), ["lembrete", "avaliacao"]))
    for chave, ini, fim, antecedencia, titulo, obs, rotulos in pendentes:
        if chave in enviados or not (0 <= (ini - h).days <= antecedencia):
            continue
        datas = f"{ini:%d/%m/%Y}" + (f" a {fim:%d/%m/%Y}" if fim != ini else "")
        corpo = f"**{titulo}**\n\n📅 {datas} ({quando(ini, fim, h)})\n\n{obs}\n\n_Lembrete automático gerado a partir de `dados/`._"
        if gh.abrir_issue(f"⏰ {titulo} — {ini:%d/%m}", corpo, rotulos):
            enviados[chave] = str(h)
            salvar_json(ARQ_ALERTAS, enviados)


def main() -> None:
    h = hoje()
    linhas = ["<!-- painel:inicio -->", "<!-- Gerado por scripts/painel.py. Não edite à mão. -->", ""]
    linhas += secao_hoje(h) + secao_prazos(h) + secao_progresso() + secao_radar()
    linhas += [f"<sub>Painel atualizado automaticamente em {h:%d/%m/%Y}.</sub>", "<!-- painel:fim -->"]
    readme = README.read_text(encoding="utf-8")
    novo = re.sub(r"<!-- painel:inicio -->.*?<!-- painel:fim -->", lambda _: "\n".join(linhas), readme, flags=re.S)
    README.write_text(novo, encoding="utf-8")
    lembretes(h)
    print("Painel atualizado.")


if __name__ == "__main__":
    main()
