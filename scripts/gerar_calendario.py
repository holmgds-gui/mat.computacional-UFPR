"""Gera os calendários .ics e publica a interface do SIGA+ UFPR em site/ a partir de dados/.

Arquivos gerados:
  site/calendario.ics  – tudo (prazos + aulas + avaliações)
  site/prazos.ics      – calendário acadêmico, eventos e avaliações
  site/aulas.ics       – grade horária semanal
  site/estado.json     – estado público consolidado (sem dados de privado/)
  site/index.html, site/style.css, site/app.js – interface web SIGA+ UFPR

Uso: python scripts/gerar_calendario.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

from comum import DADOS, FUSO, RAIZ, SITE, avaliacoes, como_data, eventos_do_calendario, hoje, ler_yaml

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


def exportar_site_app() -> None:
    """Copia os arquivos estáticos de app/static/ para site/ e gera site/estado.json público."""
    app_dir = RAIZ / "app"
    static_dir = app_dir / "static"
    if not static_dir.exists():
        return
    for arq in ("index.html", "style.css", "app.js"):
        orig = static_dir / arq
        if orig.exists():
            shutil.copy2(orig, SITE / arq)

    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    import servidor  # noqa: E402

    estado_pub = servidor.montar_estado_completo()
    # Nunca expor notas/faltas reais de privado/ no JSON estático público do GitHub Pages
    estado_pub["privado"] = {
        "disciplinas": {},
        "plano_proximo_semestre": ["CI185", "CMI021", "CMI022", "CMI023", "CE035"],
        "metas_semestre": [
            {"texto": "Importar as Fichas 2 (planos de ensino) do SIGA: datas de prova e critérios", "feita": False},
            {"texto": "Cadastrar as datas de prova em dados/avaliacoes.yml", "feita": False},
            {"texto": "Ir à SIEPE (19 a 23/10) e guardar o certificado", "feita": False},
            {"texto": "Conversar com 2 ou 3 professores sobre iniciação científica em otimização ou IA", "feita": False},
            {"texto": "Criar Lattes e ORCID", "feita": False},
        ],
    }
    estado_pub["modo_estatico"] = True
    (SITE / "estado.json").write_text(
        json.dumps(estado_pub, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


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

    exportar_site_app()
    print(f"Calendário e App Web gerados: {len(blocos_prazos)} prazos/eventos, {len(blocos_aulas)} séries de aula → {SITE}")


if __name__ == "__main__":
    main()
