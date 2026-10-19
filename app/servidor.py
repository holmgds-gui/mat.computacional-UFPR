"""Servidor Web do SIGA+ UFPR (Matemática Industrial).

Roda localmente (python app/servidor.py) e no Google Cloud Run (container).
Lê e atualiza diretamente os arquivos YAML de `dados/` (sincronizando com o GitHub)
e mantém notas, faltas e planejamentos pessoais em `privado/historico.yml`.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

# Garante que scripts/ está no sys.path para reutilizar comum.py, painel.py e gerar_calendario.py
RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import comum  # noqa: E402
import gerar_calendario  # noqa: E402
import painel  # noqa: E402

DADOS = comum.DADOS
ESTADO = comum.ESTADO
PRIVADO = RAIZ / "privado"
ARQ_HISTORICO = PRIVADO / "historico.yml"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def ler_historico_privado() -> dict:
    """Lê (ou inicializa) o arquivo privado/historico.yml com notas, faltas e metas."""
    PRIVADO.mkdir(parents=True, exist_ok=True)
    if not ARQ_HISTORICO.exists():
        inicial = {
            "disciplinas": {
                "CE009": {"p1": None, "p2": None, "p3": None, "trabalhos": None, "exame": None, "faltas_horas": 0, "link_virtual": "", "notas_rapidas": ""},
                "CF109": {"p1": None, "p2": None, "p3": None, "trabalhos": None, "exame": None, "faltas_horas": 0, "link_virtual": "", "notas_rapidas": ""},
                "CI1164": {"p1": None, "p2": None, "p3": None, "trabalhos": None, "exame": None, "faltas_horas": 0, "link_virtual": "", "notas_rapidas": ""},
                "TT080": {"p1": None, "p2": None, "p3": None, "trabalhos": None, "exame": None, "faltas_horas": 0, "link_virtual": "", "notas_rapidas": ""},
                "TT081": {"p1": None, "p2": None, "p3": None, "trabalhos": None, "exame": None, "faltas_horas": 0, "link_virtual": "", "notas_rapidas": ""},
                "CI1068": {"p1": None, "p2": None, "p3": None, "trabalhos": None, "exame": None, "faltas_horas": 0, "link_virtual": "", "notas_rapidas": ""},
            },
            "historico_concluidas": {
                "CI182": {"nota": None, "frequencia": 100, "semestre": "2026-1"},
                "CMI011": {"nota": None, "frequencia": 100, "semestre": "2026-1"},
                "CMI012": {"nota": None, "frequencia": 100, "semestre": "2026-1"},
                "CMI013": {"nota": None, "frequencia": 100, "semestre": "2026-1"},
                "CMI014": {"nota": None, "frequencia": 100, "semestre": "2026-1"},
            },
            "plano_proximo_semestre": ["CI185", "CMI021", "CMI022", "CMI023", "CE035"],
            "metas_semestre": [
                {"texto": "Importar as Fichas 2 (planos de ensino) do SIGA: datas de prova e critérios", "feita": False},
                {"texto": "Cadastrar as datas de prova em dados/avaliacoes.yml", "feita": False},
                {"texto": "Ir à SIEPE (19 a 23/10) e guardar o certificado", "feita": False},
                {"texto": "Conversar com 2 ou 3 professores sobre iniciação científica em otimização ou IA", "feita": False},
                {"texto": "Criar Lattes e ORCID", "feita": False},
            ],
        }
        salvar_historico_privado(inicial)
        return inicial
    return comum.ler_yaml(ARQ_HISTORICO)


def salvar_historico_privado(dados: dict) -> None:
    PRIVADO.mkdir(parents=True, exist_ok=True)
    cabecalho = (
        "# Dados acadêmicos privados — NUNCA enviados ao GitHub público (.gitignore)\n"
        "# Gerenciado pelo app SIGA+ UFPR.\n\n"
    )
    corpo = yaml.safe_dump(dados, allow_unicode=True, sort_keys=False, default_flow_style=False)
    ARQ_HISTORICO.write_text(cabecalho + corpo, encoding="utf-8")


def extrair_info_disciplinas() -> dict[str, dict]:
    """Lê os README.md de cada pasta em disciplinas/ para extrair ementa, bibliografia e arquivos."""
    pasta_disc = RAIZ / "disciplinas"
    resultado: dict[str, dict] = {}
    if not pasta_disc.exists():
        return resultado

    for sub in sorted(pasta_disc.iterdir()):
        if not sub.is_dir():
            continue
        codigo = sub.name.split("-")[0].upper()
        readme = sub / "README.md"
        ementa = ""
        bibliografia: list[str] = []
        if readme.exists():
            txt = readme.read_text(encoding="utf-8")
            m_em = re.search(r"##\s+Ementa\s+(.+?)(?=\n##|\Z)", txt, flags=re.S)
            if m_em:
                ementa = m_em.group(1).strip()
            m_bib = re.search(r"##\s+Bibliografia básica\s+(.+?)(?=\n##|\Z)", txt, flags=re.S)
            if m_bib:
                bibliografia = [
                    lin.lstrip("- ").strip()
                    for lin in m_bib.group(1).strip().splitlines()
                    if lin.strip().startswith("-")
                ]
        arquivos: dict[str, list[str]] = {}
        for cat in ("anotacoes", "listas", "provas", "codigo"):
            p_cat = sub / cat
            if p_cat.exists():
                arquivos[cat] = [
                    f.name for f in sorted(p_cat.iterdir()) if f.is_file() and f.name != ".gitkeep"
                ]
            else:
                arquivos[cat] = []

        resultado[codigo] = {
            "pasta": sub.name,
            "ementa": ementa,
            "bibliografia": bibliografia,
            "arquivos": arquivos,
        }
    return resultado


def status_git() -> dict:
    """Retorna informações sobre o estado atual do repositório Git e integração GitHub."""
    modificados: list[str] = []
    branch = "main"
    try:
        res_b = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res_b.returncode == 0:
            branch = res_b.stdout.strip()
        res_s = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res_s.returncode == 0:
            modificados = [lin.strip() for lin in res_s.stdout.splitlines() if lin.strip()]
    except Exception:
        pass

    return {
        "branch": branch,
        "modificados": modificados,
        "tem_alteracoes": len(modificados) > 0,
        "github_token_configurado": bool(os.environ.get("GITHUB_TOKEN")),
        "github_repo": os.environ.get("GITHUB_REPOSITORY", "holmgds-gui/mat.computacional-UFPR"),
        "cloud_run": bool(os.environ.get("K_SERVICE")),
    }


def regenerar_derivados() -> None:
    """Atualiza o painel do README.md e os arquivos .ics do calendário."""
    try:
        painel.main()
    except Exception as e:
        print(f"[aviso] falha ao atualizar painel: {e}")
    try:
        gerar_calendario.main()
    except Exception as e:
        print(f"[aviso] falha ao gerar calendario: {e}")


def serializar_datas(obj):
    if isinstance(obj, (dt.date, dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): serializar_datas(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serializar_datas(x) for x in obj]
    return obj


def montar_estado_completo() -> dict:
    h = comum.hoje()
    curso = comum.ler_yaml(DADOS / "curso.yml")
    grade = comum.ler_yaml(DADOS / "grade.yml")
    sem_atual = curso.get("semestre_atual", "2026-2")
    arq_horario = DADOS / f"horario-{sem_atual}.yml"
    horario = comum.ler_yaml(arq_horario) if arq_horario.exists() else {"aulas": [], "sem_aula": []}
    avaliacoes_lista = comum.ler_yaml(DADOS / "avaliacoes.yml").get("avaliacoes") or []
    ativ_doc = comum.ler_yaml(DADOS / "atividades.yml")
    calendario = comum.eventos_do_calendario()
    radar_log = comum.ler_json(ESTADO / "radar-log.json", [])
    fontes = comum.ler_yaml(DADOS / "fontes.yml").get("fontes") or []
    privado = ler_historico_privado()
    disc_info = extrair_info_disciplinas()

    # Calcula estatísticas de integralização
    todas_obrig = [d for sem in grade.get("semestres", {}).values() for d in sem]
    concluidas_codigos = {
        d["codigo"] for d in todas_obrig if d.get("status") in ("concluida", "dispensada")
    }
    ch_obrig_concluidas = sum(
        d["ch"] for d in todas_obrig if d.get("status") in ("concluida", "dispensada")
    )
    ch_obrig_cursando = sum(d["ch"] for d in todas_obrig if d.get("status") == "cursando")
    a_confirmar = [
        d["codigo"]
        for d in todas_obrig
        if d.get("status") != "pendente" and d.get("confirmado") is False
    ]

    opts = grade.get("optativas_planejadas") or []
    ch_opt_concluidas = sum(o.get("ch", 60) for o in opts if o.get("status") == "concluida")
    ch_opt_cursando = sum(o.get("ch", 60) for o in opts if o.get("status") == "cursando")

    limites_form = ativ_doc.get("limites_formativas") or {}
    atividades_lista = ativ_doc.get("atividades") or []
    por_cat_bruto: dict[str, float] = {}
    ext_total = 0.0
    ext_iv = 0.0
    por_ace: dict[str, float] = {"ACE-I": 0, "ACE-II": 0, "ACE-III": 0, "ACE-IV": 0, "ACE-V": 0}

    for a in atividades_lista:
        hrs = float(a.get("horas", 0))
        if a.get("conta_como") == "formativa":
            cat = a.get("categoria", "")
            por_cat_bruto[cat] = por_cat_bruto.get(cat, 0.0) + hrs
        else:
            cat = a.get("categoria", "ACE-III")
            ext_total += hrs
            por_ace[cat] = por_ace.get(cat, 0.0) + hrs
            if cat == "ACE-IV":
                ext_iv += hrs

    por_cat_validado = {
        cat: min(por_cat_bruto.get(cat, 0.0), float(lim))
        for cat, lim in limites_form.items()
    }
    ch_formativas_total = sum(por_cat_validado.values())

    # Enriquecer disciplinas da grade com info de pré-requisitos liberados
    semestres_enriquecidos = {}
    for num_sem, lista_d in grade.get("semestres", {}).items():
        nova_lista = []
        for d in lista_d:
            item = dict(d)
            prereqs = item.get("prereq") or []
            faltam_prereq = [p for p in prereqs if p not in concluidas_codigos]
            item["prereq_liberado"] = len(faltam_prereq) == 0
            item["prereq_faltando"] = faltam_prereq
            if item["codigo"] in disc_info:
                item["detalhes"] = disc_info[item["codigo"]]
            nova_lista.append(item)
        semestres_enriquecidos[str(num_sem)] = nova_lista

    return serializar_datas(
        {
            "hoje": {
                "data": h.isoformat(),
                "data_br": h.strftime("%d/%m/%Y"),
                "dia_semana_cod": ["seg", "ter", "qua", "qui", "sex", "sab", "dom"][h.weekday()],
                "dia_semana_nome": [
                    "Segunda-feira",
                    "Terça-feira",
                    "Quarta-feira",
                    "Quinta-feira",
                    "Sexta-feira",
                    "Sábado",
                    "Domingo",
                ][h.weekday()],
            },
            "curso": curso,
            "progresso": {
                "obrigatorias": {
                    "concluidas": ch_obrig_concluidas,
                    "cursando": ch_obrig_cursando,
                    "meta": curso["carga_horaria"]["obrigatorias"],
                },
                "optativas": {
                    "concluidas": ch_opt_concluidas,
                    "cursando": ch_opt_cursando,
                    "meta": curso["carga_horaria"]["optativas"],
                },
                "formativas": {
                    "concluidas": ch_formativas_total,
                    "meta": curso["carga_horaria"]["formativas"],
                    "por_categoria_bruto": por_cat_bruto,
                    "por_categoria_validado": por_cat_validado,
                    "limites": limites_form,
                },
                "extensao": {
                    "concluidas": ext_total,
                    "meta": curso["carga_horaria"]["extensao"],
                    "ace_iv": ext_iv,
                    "ace_iv_meta": curso["carga_horaria"]["extensao_ace_iv_minimo"],
                    "por_ace": por_ace,
                },
                "a_confirmar_siga": a_confirmar,
            },
            "grade": {
                "semestres": semestres_enriquecidos,
                "optativas_planejadas": opts,
                "eletivas": grade.get("eletivas") or [],
                "optativas_extensao": grade.get("optativas_extensao") or [],
            },
            "horario": horario,
            "avaliacoes": avaliacoes_lista,
            "atividades": atividades_lista,
            "calendario": calendario,
            "radar": radar_log,
            "fontes_radar": fontes,
            "privado": privado,
            "disciplinas_info": disc_info,
            "git": status_git(),
        }
    )


def atualizar_status_grade(codigo: str, novo_status: str | None, confirmado: bool | None) -> bool:
    """Atualiza o status e/ou confirmação de uma disciplina em dados/grade.yml preservando comentários."""
    arq = DADOS / "grade.yml"
    linhas = arq.read_text(encoding="utf-8").splitlines()
    codigo_upper = codigo.upper().strip()
    alterou = False

    for i, lin in enumerate(linhas):
        if re.search(rf"\bcodigo:\s*{re.escape(codigo_upper)}\b", lin):
            nova = lin
            if novo_status is not None:
                if "status:" in nova:
                    nova = re.sub(r"status:\s*[a-zA-Z_]+", f"status: {novo_status}", nova)
                else:
                    nova = nova.rstrip("}") + f", status: {novo_status}}}"
            if confirmado is not None:
                val_str = "true" if confirmado else "false"
                if "confirmado:" in nova:
                    nova = re.sub(r"confirmado:\s*(true|false)", f"confirmado: {val_str}", nova)
                else:
                    nova = re.sub(
                        r"(status:\s*[a-zA-Z_]+)",
                        rf"\1, confirmado: {val_str}",
                        nova,
                    )
            linhas[i] = nova
            alterou = True
            break

    if alterou:
        arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        comum.ler_yaml(arq)  # valida YAML
        regenerar_derivados()
    return alterou


def confirmar_todas_1_semestre() -> int:
    arq = DADOS / "grade.yml"
    txt = arq.read_text(encoding="utf-8")
    novo, n = re.subn(r"confirmado:\s*false", "confirmado: true", txt)
    if n > 0:
        arq.write_text(novo, encoding="utf-8")
        comum.ler_yaml(arq)
        regenerar_derivados()
    return n


def salvar_lista_yaml(arquivo: Path, chave_lista: str, itens: list[dict]) -> None:
    """Substitui a lista final de um arquivo YAML (como avaliacoes.yml ou atividades.yml) mantendo o cabeçalho."""
    texto = arquivo.read_text(encoding="utf-8")
    padrao = rf"^{re.escape(chave_lista)}:.*$"
    m = re.search(padrao, texto, flags=re.M | re.S)
    cabecalho = texto[: m.start()] if m else texto.rstrip() + "\n\n"
    if not itens:
        bloco = f"{chave_lista}: []\n"
    else:
        linhas_itens = [f"{chave_lista}:"]
        for it in itens:
            linhas_itens.append("  - " + json.dumps(it, ensure_ascii=False))
        bloco = "\n".join(linhas_itens) + "\n"
    arquivo.write_text(cabecalho + bloco, encoding="utf-8")
    comum.ler_yaml(arquivo)
    regenerar_derivados()


def atualizar_aula_horario(codigo: str, professor: str, sala: str) -> bool:
    """Atualiza professor e sala de uma disciplina em dados/horario-2026-2.yml."""
    curso = comum.ler_yaml(DADOS / "curso.yml")
    arq = DADOS / f"horario-{curso.get('semestre_atual', '2026-2')}.yml"
    if not arq.exists():
        return False
    texto = arq.read_text(encoding="utf-8")
    linhas = texto.splitlines()
    alterou = False
    for i, lin in enumerate(linhas):
        if re.search(rf"\bcodigo:\s*{re.escape(codigo.upper())}\b", lin):
            lin_nova = re.sub(r'professor:\s*"[^"]*"', f'professor: "{professor}"', lin)
            lin_nova = re.sub(r'sala:\s*"[^"]*"', f'sala: "{sala}"', lin_nova)
            linhas[i] = lin_nova
            alterou = True
            break
    if alterou:
        arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        comum.ler_yaml(arq)
        regenerar_derivados()
    return alterou


def sincronizar_github(mensagem: str) -> dict:
    """Sincroniza alterações com o GitHub via Git local ou via API REST do GitHub (para Cloud Run)."""
    regenerar_derivados()
    msg = (mensagem or "Atualização via SIGA+ UFPR").strip()

    # Modo 1: GitHub Contents API (quando rodando em container serverless sem git push configurado, mas com GITHUB_TOKEN)
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "holmgds-gui/mat.computacional-UFPR")
    usar_api = bool(os.environ.get("K_SERVICE") and token)

    if usar_api:
        arquivos_alvo = [
            "README.md",
            "dados/grade.yml",
            "dados/avaliacoes.yml",
            "dados/atividades.yml",
            "dados/horario-2026-2.yml",
        ]
        enviados = []
        for rel in arquivos_alvo:
            cam = RAIZ / rel
            if not cam.exists():
                continue
            conteudo_b64 = base64.b64encode(cam.read_bytes()).decode("ascii")
            url = f"https://api.github.com/repos/{repo}/contents/{rel}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": comum.USER_AGENT,
            }
            sha = None
            try:
                req_get = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req_get, timeout=20) as r:
                    dados_arq = json.loads(r.read().decode("utf-8"))
                    sha = dados_arq.get("sha")
                    remoto_b64 = (dados_arq.get("content") or "").replace("\n", "")
                    if remoto_b64 == conteudo_b64:
                        continue
            except Exception:
                pass
            corpo = {"message": msg, "content": conteudo_b64}
            if sha:
                corpo["sha"] = sha
            req_put = urllib.request.Request(
                url,
                data=json.dumps(corpo).encode("utf-8"),
                method="PUT",
                headers=headers,
            )
            with urllib.request.urlopen(req_put, timeout=25) as r:
                if r.status in (200, 201):
                    enviados.append(rel)
        return {
            "ok": True,
            "modo": "github_api",
            "mensagem": f"Sincronizado via API do GitHub ({len(enviados)} arquivo(s) atualizado(s)).",
            "arquivos": enviados,
        }

    # Modo 2: Git CLI local
    try:
        subprocess.run(["git", "add", "dados/", "README.md"], cwd=RAIZ, check=True, timeout=10)
        res_diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=RAIZ, timeout=10
        )
        if res_diff.returncode == 0:
            return {
                "ok": True,
                "modo": "git_local",
                "mensagem": "Nenhuma alteração pendente em dados/ ou README.md para commitar.",
            }
        res_commit = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res_commit.returncode != 0:
            return {
                "ok": False,
                "modo": "git_local",
                "mensagem": f"Erro no git commit: {res_commit.stderr or res_commit.stdout}",
            }
        res_push = subprocess.run(
            ["git", "push"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if res_push.returncode != 0:
            return {
                "ok": True,
                "modo": "git_local_sem_push",
                "mensagem": f"Commit local criado! (Push pendente: {res_push.stderr.strip()})",
            }
        return {
            "ok": True,
            "modo": "git_local",
            "mensagem": "Commit realizado e enviado (git push) para o GitHub com sucesso!",
        }
    except Exception as e:
        return {"ok": False, "modo": "erro", "mensagem": f"Falha ao sincronizar: {e}"}


class SigaPlusHandler(BaseHTTPRequestHandler):
    """Handler HTTP para a interface e endpoints JSON do SIGA+ UFPR."""

    def log_message(self, format: str, *args) -> None:
        # Log mais limpo no terminal
        sys.stderr.write(f"[SIGA+] {self.address_string()} - {format % args}\n")

    def _verificar_acesso(self) -> bool:
        """Verifica autenticação quando configurado no Google Cloud Run (IAP ou email autorizado)."""
        email_permitido = os.environ.get("ALLOWED_EMAIL", "").strip().lower()
        if not email_permitido:
            return True
        # Header injetado automaticamente pelo Google Cloud Identity-Aware Proxy (IAP)
        iap_email = self.headers.get("X-Goog-Authenticated-User-Email", "").lower()
        # Formato do IAP: accounts.google.com:usuario@ufpr.br
        if email_permitido in iap_email:
            return True
        token_app = os.environ.get("APP_SECRET_TOKEN", "").strip()
        if token_app and self.headers.get("X-App-Token") == token_app:
            return True
        self._responder_json({"erro": "Acesso restrito ao proprietário do repositório."}, status=403)
        return False

    def _responder_json(self, dados: dict | list, status: int = 200) -> None:
        corpo = json.dumps(serializar_datas(dados), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_corpo_json(self) -> dict:
        tam = int(self.headers.get("Content-Length", "0"))
        if tam <= 0:
            return {}
        bruto = self.rfile.read(tam)
        return json.loads(bruto.decode("utf-8"))

    def do_GET(self) -> None:
        if not self._verificar_acesso():
            return
        caminho = urllib.parse.urlparse(self.path).path

        if caminho == "/api/estado":
            self._responder_json(montar_estado_completo())
            return

        # Servir arquivos .ics gerados em site/
        if caminho in ("/calendario.ics", "/prazos.ics", "/aulas.ics"):
            arq_ics = comum.SITE / caminho.lstrip("/")
            if not arq_ics.exists():
                gerar_calendario.main()
            if arq_ics.exists():
                conteudo = arq_ics.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar; charset=utf-8")
                self.send_header("Content-Length", str(len(conteudo)))
                self.end_headers()
                self.wfile.write(conteudo)
                return

        # Servir arquivos estáticos de app/static/
        if caminho == "/" or caminho == "/index.html":
            arq = STATIC_DIR / "index.html"
        else:
            rel = caminho.lstrip("/")
            arq = (STATIC_DIR / rel).resolve()
            if not str(arq).startswith(str(STATIC_DIR.resolve())):
                self.send_error(403)
                return

        if arq.exists() and arq.is_file():
            tipo, _ = mimetypes.guess_type(str(arq))
            conteudo = arq.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{tipo or 'text/plain'}; charset=utf-8")
            self.send_header("Content-Length", str(len(conteudo)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(conteudo)
        else:
            self.send_error(404, "Arquivo nao encontrado")

    def do_POST(self) -> None:
        if not self._verificar_acesso():
            return
        caminho = urllib.parse.urlparse(self.path).path
        try:
            corpo = self._ler_corpo_json()
        except Exception as e:
            self._responder_json({"ok": False, "erro": f"JSON inválido: {e}"}, status=400)
            return

        try:
            if caminho == "/api/grade/atualizar":
                codigo = str(corpo.get("codigo", "")).strip()
                status_novo = corpo.get("status")
                confirmado = corpo.get("confirmado")
                ok = atualizar_status_grade(codigo, status_novo, confirmado)
                self._responder_json({"ok": ok, "estado": montar_estado_completo()})
                return

            if caminho == "/api/grade/confirmar-1sem":
                n = confirmar_todas_1_semestre()
                self._responder_json({"ok": True, "confirmadas": n, "estado": montar_estado_completo()})
                return

            if caminho == "/api/avaliacoes/adicionar":
                arq = DADOS / "avaliacoes.yml"
                atuais = comum.ler_yaml(arq).get("avaliacoes") or []
                atuais = [serializar_datas(a) for a in atuais]
                novo = {
                    "codigo": str(corpo["codigo"]).upper().strip(),
                    "titulo": str(corpo["titulo"]).strip()[:120],
                    "data": dt.date.fromisoformat(str(corpo["data"]).strip()).isoformat(),
                    "tipo": str(corpo.get("tipo") or "prova").strip(),
                }
                if corpo.get("hora"):
                    novo["hora"] = str(corpo["hora"]).strip()
                if corpo.get("alerta") is not None and str(corpo["alerta"]).strip() != "":
                    novo["alerta"] = int(corpo["alerta"])
                if corpo.get("obs"):
                    novo["obs"] = str(corpo["obs"]).strip()[:500]
                atuais.append(novo)
                atuais.sort(key=lambda x: str(x.get("data", "")))
                salvar_lista_yaml(arq, "avaliacoes", atuais)
                self._responder_json({"ok": True, "estado": montar_estado_completo()})
                return

            if caminho == "/api/avaliacoes/remover":
                idx = int(corpo["indice"])
                arq = DADOS / "avaliacoes.yml"
                atuais = [serializar_datas(a) for a in (comum.ler_yaml(arq).get("avaliacoes") or [])]
                if 0 <= idx < len(atuais):
                    atuais.pop(idx)
                    salvar_lista_yaml(arq, "avaliacoes", atuais)
                self._responder_json({"ok": True, "estado": montar_estado_completo()})
                return

            if caminho == "/api/atividades/adicionar":
                arq = DADOS / "atividades.yml"
                atuais = [serializar_datas(a) for a in (comum.ler_yaml(arq).get("atividades") or [])]
                novo = {
                    "titulo": str(corpo["titulo"]).strip()[:150],
                    "data": dt.date.fromisoformat(str(corpo["data"]).strip()).isoformat(),
                    "horas": float(str(corpo["horas"]).replace(",", ".")),
                    "conta_como": str(corpo["conta_como"]).strip(),
                    "categoria": str(corpo["categoria"]).strip(),
                    "certificado": bool(corpo.get("certificado", False)),
                }
                if corpo.get("obs"):
                    novo["obs"] = str(corpo["obs"]).strip()[:500]
                atuais.append(novo)
                salvar_lista_yaml(arq, "atividades", atuais)
                self._responder_json({"ok": True, "estado": montar_estado_completo()})
                return

            if caminho == "/api/atividades/remover":
                idx = int(corpo["indice"])
                arq = DADOS / "atividades.yml"
                atuais = [serializar_datas(a) for a in (comum.ler_yaml(arq).get("atividades") or [])]
                if 0 <= idx < len(atuais):
                    atuais.pop(idx)
                    salvar_lista_yaml(arq, "atividades", atuais)
                self._responder_json({"ok": True, "estado": montar_estado_completo()})
                return

            if caminho == "/api/horario/atualizar":
                ok = atualizar_aula_horario(
                    str(corpo.get("codigo", "")),
                    str(corpo.get("professor", "")),
                    str(corpo.get("sala", "")),
                )
                self._responder_json({"ok": ok, "estado": montar_estado_completo()})
                return

            if caminho == "/api/privado/salvar":
                atual = ler_historico_privado()
                if "disciplinas" in corpo:
                    atual["disciplinas"] = corpo["disciplinas"]
                if "historico_concluidas" in corpo:
                    atual["historico_concluidas"] = corpo["historico_concluidas"]
                if "plano_proximo_semestre" in corpo:
                    atual["plano_proximo_semestre"] = corpo["plano_proximo_semestre"]
                if "metas_semestre" in corpo:
                    atual["metas_semestre"] = corpo["metas_semestre"]
                salvar_historico_privado(atual)
                self._responder_json({"ok": True, "estado": montar_estado_completo()})
                return

            if caminho == "/api/github/sincronizar":
                res = sincronizar_github(corpo.get("mensagem", "Atualização via SIGA+ UFPR"))
                self._responder_json({**res, "estado": montar_estado_completo()})
                return

            self._responder_json({"ok": False, "erro": "Rota não encontrada"}, status=404)
        except Exception as e:
            self._responder_json({"ok": False, "erro": str(e)}, status=500)


def main() -> None:
    porta = int(os.environ.get("PORT", "8080"))
    host = "0.0.0.0" if os.environ.get("K_SERVICE") else "127.0.0.1"
    servidor = ThreadingHTTPServer((host, porta), SigaPlusHandler)
    print(f"🚀 SIGA+ UFPR (Matemática Industrial) rodando em: http://{host}:{porta}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
        servidor.server_close()


if __name__ == "__main__":
    main()
