"""Gera os calendários .ics (e uma página índice) em site/ a partir de dados/.

Arquivos gerados:
  site/calendario.ics  – tudo (prazos + aulas + avaliações)
  site/prazos.ics      – calendário acadêmico, eventos e avaliações
  site/aulas.ics       – grade horária semanal
  site/index.html      – página com os links de assinatura

Uso: python scripts/gerar_calendario.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html

from comum import DADOS, FUSO, SITE, avaliacoes, como_data, eventos_do_calendario, hoje, ler_yaml

TZID = "America/Sao_Paulo"
DIAS = {"seg": ("MO", 0), "ter": ("TU", 1), "qua": ("WE", 2), "qui": ("TH", 3), "sex": ("FR", 4), "sab": ("SA", 5)}
EMOJI = {"letivo": "🎓", "matricula": "📝", "prazo": "⏳", "exame": "🧪", "evento": "🎤",
         "feriado": "🌴", "ic": "🔬", "prova": "🧪", "trabalho": "📦", "lista": "📄", "seminario": "🗣️"}

VTIMEZONE = [
    "BEGIN:VTIMEZONE", f"TZID:{TZID}",
    "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:-0300", "TZOFFSETTO:-0300", "TZNAME:-03",
    "END:STANDARD", "END:VTIMEZONE",
]


def esc(texto: str) -> str:
    return (str(texto).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n"))


def dobrar(linha: str) -> list[str]:
    """Quebra linhas com mais de 75 octetos (RFC 5545 §3.1)."""
    partes, atual = [], ""
    for ch in linha:
        limite = 75 if not partes else 74
        if len((atual + ch).encode()) > limite:
            partes.append(atual)
            atual = ch
        else:
            atual += ch
    partes.append(atual)
    return [partes[0]] + [" " + p for p in partes[1:]]


def uid(*partes) -> str:
    return hashlib.sha1("|".join(map(str, partes)).encode()).hexdigest()[:20] + "@matind-ufpr"


def d(data: dt.date) -> str:
    return data.strftime("%Y%m%d")


def dia_inteiro(ev: dict, carimbo: str) -> list[str]:
    linhas = [
        "BEGIN:VEVENT",
        f"UID:{uid('cal', ev['titulo'], ev['inicio'])}",
        f"DTSTAMP:{carimbo}",
        f"DTSTART;VALUE=DATE:{d(ev['inicio'])}",
        f"DTEND;VALUE=DATE:{d(ev['fim'] + dt.timedelta(days=1))}",  # DTEND é exclusivo
        f"SUMMARY:{esc(EMOJI.get(ev.get('tipo'), '📌') + ' ' + ev['titulo'])}",
        f"CATEGORIES:{esc(ev.get('tipo', 'evento'))}",
        "TRANSP:TRANSPARENT",
    ]
    if ev.get("obs"):
        linhas.append(f"DESCRIPTION:{esc(ev['obs'])}")
    return linhas + ["END:VEVENT"]


def aulas_semanais(horario: dict, carimbo: str) -> list[list[str]]:
    inicio, fim = como_data(horario["inicio"]), como_data(horario["fim"])
    sem_aula = [como_data(x) for x in horario.get("sem_aula") or []]
    # UNTIL precisa estar em UTC quando DTSTART tem TZID: fim do último dia (23:59:59 BRT).
    ate = dt.datetime.combine(fim, dt.time(23, 59, 59), FUSO).astimezone(dt.timezone.utc)
    blocos = []
    for aula in horario["aulas"]:
        h_ini = dt.time.fromisoformat(aula["inicio"])
        h_fim = dt.time.fromisoformat(aula["fim"])
        for dia in aula["dias"]:
            byday, wd = DIAS[dia]
            # DTSTART tem de cair no próprio dia da semana, senão vira uma aula fantasma
            primeiro = inicio + dt.timedelta(days=(wd - inicio.weekday()) % 7)
            exdates = [x for x in sem_aula if x.weekday() == wd and primeiro <= x <= fim]
            linhas = [
                "BEGIN:VEVENT",
                f"UID:{uid('aula', horario['semestre'], aula['codigo'], dia)}",
                f"DTSTAMP:{carimbo}",
                f"DTSTART;TZID={TZID}:{d(primeiro)}T{h_ini.strftime('%H%M%S')}",
                f"DTEND;TZID={TZID}:{d(primeiro)}T{h_fim.strftime('%H%M%S')}",
                f"RRULE:FREQ=WEEKLY;BYDAY={byday};UNTIL={ate.strftime('%Y%m%dT%H%M%SZ')}",
            ]
            for x in exdates:
                linhas.append(f"EXDATE;TZID={TZID}:{d(x)}T{h_ini.strftime('%H%M%S')}")
            linhas += [
                f"SUMMARY:{esc(aula['codigo'] + ' — ' + aula['nome'])}",
                f"LOCATION:{esc(aula.get('sala') or horario.get('local_padrao', ''))}",
                f"DESCRIPTION:{esc('Professor(a): ' + aula.get('professor', 'a definir'))}",
                "CATEGORIES:aula",
                "END:VEVENT",
            ]
            blocos.append(linhas)
    return blocos


def avaliacao(av: dict, carimbo: str) -> list[str]:
    titulo = f"{EMOJI.get(av.get('tipo'), '🧪')} {av['codigo']} — {av['titulo']}"
    linhas = ["BEGIN:VEVENT", f"UID:{uid('aval', av['codigo'], av['titulo'])}", f"DTSTAMP:{carimbo}"]
    if av.get("hora"):
        ini = dt.datetime.combine(av["data"], dt.time.fromisoformat(av["hora"]))
        fim = ini + dt.timedelta(hours=float(av.get("duracao_h", 2)))
        linhas += [f"DTSTART;TZID={TZID}:{ini.strftime('%Y%m%dT%H%M%S')}",
                   f"DTEND;TZID={TZID}:{fim.strftime('%Y%m%dT%H%M%S')}"]
    else:
        linhas += [f"DTSTART;VALUE=DATE:{d(av['data'])}",
                   f"DTEND;VALUE=DATE:{d(av['data'] + dt.timedelta(days=1))}"]
    linhas += [f"SUMMARY:{esc(titulo)}", f"CATEGORIES:{esc(av.get('tipo', 'prova'))}"]
    if av.get("obs"):
        linhas.append(f"DESCRIPTION:{esc(av['obs'])}")
    linhas += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(titulo)}", "TRIGGER:-P1D", "END:VALARM"]
    return linhas + ["END:VEVENT"]


def montar(nome: str, blocos: list[list[str]]) -> str:
    linhas = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//matind-ufpr//calendario academico//PT-BR",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(nome)}", f"X-WR-TIMEZONE:{TZID}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H",
        *VTIMEZONE,
    ]
    for b in blocos:
        linhas += b
    linhas.append("END:VCALENDAR")
    saida = []
    for linha in linhas:
        saida += dobrar(linha)
    return "\r\n".join(saida) + "\r\n"


def pagina_indice(proximos: list[dict]) -> str:
    itens = "\n".join(
        f"<li><time>{ev['inicio']:%d/%m}</time> {html.escape(ev['titulo'])}</li>" for ev in proximos
    ) or "<li>Nada nos próximos 30 dias.</li>"
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Calendário Matemática Industrial</title>
<style>
:root{{--bg:#fafaf7;--fg:#1d1d1b;--mut:#666;--ac:#1f6feb;--card:#fff;--bd:#e3e3dc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141414;--fg:#ececec;--mut:#9a9a9a;--ac:#58a6ff;--card:#1d1d1d;--bd:#2c2c2c}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:720px;margin:0 auto;padding:32px 16px}}
h1{{font-size:1.6rem;margin:0 0 4px}} p{{color:var(--mut)}}
.card{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin:16px 0}}
code{{word-break:break-all}} a{{color:var(--ac)}} time{{font-variant-numeric:tabular-nums;color:var(--mut);margin-right:8px}}
ul{{padding-left:18px}}
</style></head><body><main>
<h1>Calendário — Matemática Industrial UFPR</h1>
<p>Gerado automaticamente a partir do repositório. Atualizado em {hoje():%d/%m/%Y}.</p>
<div class="card"><strong>Assinar no Google Calendar:</strong> Outras agendas → <em>+</em> → <em>Do URL</em> → cole um dos links:
<ul>
<li>Tudo: <code id="t"></code></li>
<li>Só prazos, eventos e provas: <code id="p"></code></li>
<li>Só aulas: <code id="a"></code></li>
</ul></div>
<div class="card"><strong>Próximos 30 dias</strong><ul>{itens}</ul></div>
<p><a href="https://github.com/holmgds-gui/mat.computacional-UFPR">Repositório</a></p>
</main><script>
const b=location.href.replace(/[^/]*$/,'');
for(const[i,f]of[['t','calendario.ics'],['p','prazos.ics'],['a','aulas.ics']])document.getElementById(i).textContent=b+f;
</script></body></html>
"""


def main() -> None:
    carimbo = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    eventos = eventos_do_calendario()
    blocos_prazos = [dia_inteiro(ev, carimbo) for ev in eventos]
    blocos_prazos += [avaliacao(av, carimbo) for av in avaliacoes()]

    blocos_aulas = []
    for arq in sorted(DADOS.glob("horario-*.yml")):
        blocos_aulas += aulas_semanais(ler_yaml(arq), carimbo)

    SITE.mkdir(exist_ok=True)
    arquivos = {
        "calendario.ics": montar("Mat. Industrial UFPR", blocos_prazos + blocos_aulas),
        "prazos.ics": montar("Mat. Industrial — prazos e provas", blocos_prazos),
        "aulas.ics": montar("Mat. Industrial — aulas", blocos_aulas),
    }
    for nome, conteudo in arquivos.items():
        (SITE / nome).write_text(conteudo, encoding="utf-8", newline="")

    h = hoje()
    proximos = sorted((e for e in eventos if e["fim"] >= h and e["inicio"] <= h + dt.timedelta(days=30)),
                      key=lambda e: e["inicio"])
    (SITE / "index.html").write_text(pagina_indice(proximos), encoding="utf-8")
    print(f"Calendário: {len(blocos_prazos)} prazos/eventos, {len(blocos_aulas)} séries de aula → {SITE}")


if __name__ == "__main__":
    main()
