"""Cria a pasta de uma disciplina a partir de dados/grade.yml.

Uso: python scripts/nova_disciplina.py CMI031 [CMI032 ...]

Gera disciplinas/<CODIGO>-<nome>/ com README (ficha) e as subpastas
anotacoes/, listas/, provas/ e codigo/. Não sobrescreve pastas existentes.
"""

from __future__ import annotations

import sys

from comum import DADOS, RAIZ, ler_yaml, slug

DEPTOS = {"DMAT": "Departamento de Matemática", "DINF": "Departamento de Informática",
          "DEST": "Departamento de Estatística", "DFIS": "Departamento de Física",
          "DEP": "Departamento de Engenharia de Produção"}
NOME_DIA = {"seg": "Seg", "ter": "Ter", "qua": "Qua", "qui": "Qui", "sex": "Sex", "sab": "Sáb"}


def localizar(codigo: str):
    grade = ler_yaml(DADOS / "grade.yml")
    for periodo, lista in grade["semestres"].items():
        for d in lista:
            if d["codigo"] == codigo:
                return d, periodo
    for d in grade.get("optativas_planejadas") or []:
        if d["codigo"] == codigo:
            return {**d, "ch": d.get("ch", 60), "depto": d.get("depto", "")}, "optativa"
    raise SystemExit(f"{codigo} não está em dados/grade.yml")


def aula_atual(codigo: str):
    curso = ler_yaml(DADOS / "curso.yml")
    arq = DADOS / f"horario-{curso['semestre_atual']}.yml"
    if arq.exists():
        for a in ler_yaml(arq)["aulas"]:
            if a["codigo"] == codigo:
                return curso["semestre_atual"], a
    return None, None


def readme(d: dict, periodo, ementa: str = "", biblio: str = "") -> str:
    semestre, aula = aula_atual(d["codigo"])
    periodo_txt = f"{periodo}º período" if isinstance(periodo, int) else "optativa"
    linhas = [
        f"# {d['codigo']} — {d['nome']}",
        "",
        "| | |",
        "|---|---|",
        f"| **Carga horária** | {d['ch']}h |",
        f"| **Departamento** | {DEPTOS.get(d['depto'], d['depto'])} |",
        f"| **Periodização** | {periodo_txt} |",
        f"| **Pré-requisitos** | {', '.join(d.get('prereq') or []) or '—'} |",
    ]
    if aula:
        dias = ", ".join(NOME_DIA[x] for x in aula["dias"])
        linhas += [f"| **Turma {semestre}** | {dias}, {aula['inicio']}–{aula['fim']} |",
                   f"| **Professor(a)** | {aula['professor']} |"]
    linhas += [
        f"| **Ficha oficial** | [ementa (PDF)]({d['ementa']}) |" if d.get("ementa") else "| **Ficha oficial** | — |",
        "| **UFPR Virtual** | _cole aqui o link da página da disciplina_ |",
        "",
        "## Ementa",
        "",
        ementa or "_Copie a ementa da ficha oficial._",
        "",
    ]
    if biblio:
        linhas += ["## Bibliografia básica", "", biblio, ""]
    linhas += [
        "## Avaliações",
        "",
        "Cadastre provas e trabalhos em [`dados/avaliacoes.yml`](../../dados/avaliacoes.yml): eles entram no calendário",
        "e geram lembrete automático. **Notas** ficam em `privado/historico.yml`, que não vai para o GitHub.",
        "",
        "| Avaliação | Data | Peso | Conteúdo |",
        "|---|---|---|---|",
        "| | | | |",
        "",
        "## Plano de aulas / conteúdo",
        "",
        "| Semana | Conteúdo | Anotação |",
        "|---|---|---|",
        "| 1 | | |",
        "",
        "## Pastas",
        "",
        "- [`anotacoes/`](anotacoes/): resumos das aulas (Markdown, use `templates/anotacao.md`)",
        "- [`listas/`](listas/): listas de exercícios e resoluções (LaTeX: `templates/lista.tex`)",
        "- [`provas/`](provas/): provas antigas e simulados",
        "- [`codigo/`](codigo/): programas, notebooks e experimentos numéricos",
        "",
    ]
    return "\n".join(linhas)


def criar(codigo: str, ementa: str = "", biblio: str = "") -> None:
    d, periodo = localizar(codigo)
    pasta = RAIZ / "disciplinas" / (d.get("pasta") or f"{d['codigo']}-{slug(d['nome'])}")
    if pasta.exists():
        print(f"Já existe: {pasta.relative_to(RAIZ)}")
        return
    for sub in ("anotacoes", "listas", "provas", "codigo"):
        (pasta / sub).mkdir(parents=True, exist_ok=True)
        (pasta / sub / ".gitkeep").touch()
    (pasta / "README.md").write_text(readme(d, periodo, ementa, biblio), encoding="utf-8")
    print(f"Criada: {pasta.relative_to(RAIZ)}  (lembre de pôr `pasta:` em dados/grade.yml se quiser outro nome)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for c in sys.argv[1:]:
        criar(c.upper())
