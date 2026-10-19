let ESTADO = null;
let FILTRO_GRADE = "todas";
let FILTRO_CALENDARIO = "futuros";

const NOMES_CATEGORIAS_FORMATIVAS = {
  organizacao_eventos: "Organização de Eventos Acadêmicos",
  representacao_academica: "Representação Estudantil (CA, EJ, Colegiado)",
  apresentacao_trabalho: "Apresentação de Trabalho em Evento",
  extensao: "Cursos e Eventos de Extensão da UFPR",
  cursos_livres: "Cursos Livres / Idiomas / Minicursos",
  disciplina_eletiva: "Disciplina Eletiva Aprovada (ex: CI1068)",
  estagio_nao_obrigatorio: "Estágio Não Obrigatório (COE)",
  iniciacao_cientifica: "Iniciação Científica (PROPG + EVINCI)",
  monitoria: "Monitoria Acadêmica",
  participacao_eventos: "Participação em Eventos (SIEPE, Semanas)",
  programas_institucionais: "Programas Institucionais (PET, PVA)",
  voluntariado: "Voluntariado",
};

const NOMES_MODALIDADES_ACE = {
  "ACE-I": "ACE I — Disciplina Introdutória (CM001E)",
  "ACE-II": "ACE II — Monografia Extensionista (CM011E/021E)",
  "ACE-III": "ACE III — Participação em Projetos/Programas UFPR",
  "ACE-IV": "ACE IV — Equipe Organizadora / Ministrante (Mín. 90h)",
  "ACE-V": "ACE V — Extensão em Instituições Parceiras",
};

function alternarTema() {
  const claro = document.body.classList.toggle("theme-light");
  localStorage.setItem("siga_tema_claro", claro ? "1" : "0");
  const btn = document.getElementById("btn-theme-toggle");
  if (btn) btn.textContent = claro ? "Modo Escuro" : "Modo Claro";
}

function inicializarTema() {
  if (localStorage.getItem("siga_tema_claro") === "1") {
    document.body.classList.add("theme-light");
    const btn = document.getElementById("btn-theme-toggle");
    if (btn) btn.textContent = "Modo Escuro";
  }
}

function mostrarToast(msg) {
  const cont = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  cont.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

function obterTokenGitHub() {
  return (localStorage.getItem("siga_gh_token") || "").trim();
}

function salvarTokenNavegador(val) {
  localStorage.setItem("siga_gh_token", (val || "").trim());
  mostrarToast("Token do GitHub salvo neste navegador.");
}

async function ghAtualizarArquivo(caminho, transformador, msgCommit) {
  const token = obterTokenGitHub();
  if (!token) return false;
  const repo = (ESTADO && ESTADO.git && ESTADO.git.github_repo) || "holmgds-gui/mat.computacional-UFPR";
  const url = `https://api.github.com/repos/${repo}/contents/${caminho}`;
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
  const rGet = await fetch(url, { headers });
  if (!rGet.ok) throw new Error(`GitHub API (${rGet.status}) ao ler ${caminho}`);
  const meta = await rGet.json();
  const textoAtual = new TextDecoder().decode(
    Uint8Array.from(atob(meta.content.replace(/\n/g, "")), (c) => c.charCodeAt(0))
  );
  const novoTexto = transformador(textoAtual);
  if (novoTexto === textoAtual) return true;
  const bytes = new TextEncoder().encode(novoTexto);
  let bin = "";
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  const rPut = await fetch(url, {
    method: "PUT",
    headers,
    body: JSON.stringify({
      message: msgCommit || `Atualiza ${caminho} via SIGA+ UFPR`,
      content: btoa(bin),
      sha: meta.sha,
    }),
  });
  if (!rPut.ok) throw new Error(`GitHub API (${rPut.status}) ao gravar ${caminho}`);
  return true;
}

async function apiPost(url, corpo = {}) {
  if (ESTADO && ESTADO.modo_estatico) {
    if (url === "/api/privado/salvar") {
      if (corpo.disciplinas) ESTADO.privado.disciplinas = corpo.disciplinas;
      if (corpo.plano_proximo_semestre) ESTADO.privado.plano_proximo_semestre = corpo.plano_proximo_semestre;
      if (corpo.metas_semestre) ESTADO.privado.metas_semestre = corpo.metas_semestre;
      localStorage.setItem("siga_privado_local", JSON.stringify(ESTADO.privado));
      renderizarTudo();
      return { ok: true, estado: ESTADO };
    }
    if (url === "/api/grade/confirmar-1sem") {
      ESTADO.progresso.a_confirmar_siga = [];
      if (obterTokenGitHub()) {
        await ghAtualizarArquivo(
          "dados/grade.yml",
          (txt) => txt.replace(/confirmado:\s*false/g, "confirmado: true"),
          "Confirma disciplinas do 1º semestre no SIGA"
        );
      }
      renderizarTudo();
      return { ok: true, confirmadas: 5, estado: ESTADO };
    }
    if (url === "/api/grade/atualizar") {
      const cod = String(corpo.codigo || "").toUpperCase();
      Object.values(ESTADO.grade.semestres || {}).forEach((lista) =>
        lista.forEach((d) => {
          if (d.codigo === cod) {
            if (corpo.status) d.status = corpo.status;
            d.confirmado = true;
          }
        })
      );
      (ESTADO.grade.optativas_planejadas || []).forEach((o) => {
        if (o.codigo === cod && corpo.status) o.status = corpo.status;
      });
      if (obterTokenGitHub()) {
        await ghAtualizarArquivo(
          "dados/grade.yml",
          (txt) =>
            txt
              .split("\n")
              .map((lin) =>
                lin.includes(`codigo: ${cod}`)
                  ? lin.replace(/status:\s*[a-zA-Z_]+/, `status: ${corpo.status}`).replace(/confirmado:\s*false/, "confirmado: true")
                  : lin
              )
              .join("\n"),
          `Atualiza ${cod} para ${corpo.status}`
        );
      }
      renderizarTudo();
      return { ok: true, estado: ESTADO };
    }
    if (url === "/api/avaliacoes/adicionar") {
      ESTADO.avaliacoes = ESTADO.avaliacoes || [];
      const item = {
        codigo: String(corpo.codigo).toUpperCase().trim(),
        titulo: String(corpo.titulo).trim(),
        data: corpo.data,
        tipo: corpo.tipo || "prova",
      };
      if (corpo.hora) item.hora = corpo.hora;
      if (corpo.alerta) item.alerta = Number(corpo.alerta);
      if (corpo.obs) item.obs = corpo.obs;
      ESTADO.avaliacoes.push(item);
      if (obterTokenGitHub()) {
        await ghAtualizarArquivo(
          "dados/avaliacoes.yml",
          (txt) => {
            const base = txt.replace(/^avaliacoes:\s*\[\]\s*$/m, "avaliacoes:");
            return base.replace(/\s*$/, "") + "\n  - " + JSON.stringify(item) + "\n";
          },
          `Cadastra avaliação: ${item.codigo} - ${item.titulo}`
        );
      }
      renderizarTudo();
      return { ok: true, estado: ESTADO };
    }
    if (url === "/api/atividades/adicionar") {
      ESTADO.atividades = ESTADO.atividades || [];
      const item = {
        titulo: String(corpo.titulo).trim(),
        data: corpo.data,
        horas: Number(String(corpo.horas).replace(",", ".")),
        conta_como: corpo.conta_como,
        categoria: corpo.categoria,
        certificado: Boolean(corpo.certificado),
      };
      if (corpo.obs) item.obs = corpo.obs;
      ESTADO.atividades.push(item);
      if (obterTokenGitHub()) {
        await ghAtualizarArquivo(
          "dados/atividades.yml",
          (txt) => {
            const base = txt.replace(/^atividades:\s*\[\]\s*$/m, "atividades:");
            return base.replace(/\s*$/, "") + "\n  - " + JSON.stringify(item) + "\n";
          },
          `Registra atividade: ${item.titulo} (${item.horas}h)`
        );
      }
      renderizarTudo();
      return { ok: true, estado: ESTADO };
    }
    if (url === "/api/github/sincronizar") {
      if (!obterTokenGitHub()) {
        throw new Error("Cole seu GitHub Token no campo acima para sincronizar direto da nuvem.");
      }
      return { ok: true, mensagem: "Token ativo! Todas as alterações já são gravadas direto no GitHub." };
    }
  }
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  const dados = await resp.json();
  if (!resp.ok || dados.ok === false) {
    throw new Error(dados.erro || dados.mensagem || "Erro na requisição");
  }
  if (dados.estado) {
    ESTADO = dados.estado;
    renderizarTudo();
  }
  return dados;
}

async function carregarEstado() {
  inicializarTema();
  try {
    let resp = await fetch("/api/estado");
    if (!resp.ok) {
      resp = await fetch("./estado.json");
    }
    ESTADO = await resp.json();
    if (ESTADO.modo_estatico) {
      const salvo = localStorage.getItem("siga_privado_local");
      if (salvo) {
        try {
          ESTADO.privado = { ...ESTADO.privado, ...JSON.parse(salvo) };
        } catch (_) {}
      }
    }
    renderizarTudo();
  } catch (e) {
    mostrarToast("Falha ao carregar dados: " + e.message);
  }
}

function mudarAba(aba) {
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === aba);
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("active", p.id === `tab-${aba}`);
  });
}

function formatarDataBR(iso) {
  if (!iso) return "";
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

function formatarDataCurta(iso) {
  if (!iso) return "";
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

function diasEntre(isoInicio, isoHoje) {
  const d1 = new Date(isoInicio + "T00:00:00");
  const d2 = new Date(isoHoje + "T00:00:00");
  return Math.round((d1 - d2) / 86400000);
}

function renderizarTudo() {
  if (!ESTADO) return;
  renderizarTopo();
  renderizarAbaHoje();
  renderizarAbaDisciplinas();
  renderizarAbaGrade();
  renderizarAbaAvaliacoes();
  renderizarAbaAtividades();
  renderizarRadar();
}

function renderizarTopo() {
  const { hoje, curso, git, progresso } = ESTADO;
  document.getElementById("header-resumo").textContent =
    `${hoje.dia_semana_nome.toUpperCase()} · ${hoje.data_br} · SEMESTRE ${curso.semestre_atual} (${curso.periodo_atual}º PERÍODO) · CENTRO POLITÉCNICO`;

  const dot = document.getElementById("git-dot");
  const txt = document.getElementById("git-text");
  if (git.tem_alteracoes) {
    dot.className = "dot dirty";
    txt.textContent = `${git.modificados.length} alteração(ões) pendente(s)`;
  } else {
    dot.className = "dot";
    txt.textContent = `SYNC OK (${git.branch})`;
  }

  const banner = document.getElementById("banner-confirmacao-siga");
  if (progresso.a_confirmar_siga && progresso.a_confirmar_siga.length > 0) {
    banner.classList.remove("hidden");
    document.getElementById("lista-a-confirmar").textContent = progresso.a_confirmar_siga.join(", ");
  } else {
    banner.classList.add("hidden");
  }
}

/* ==================== ABA 01: HOJE & HORÁRIO ==================== */
function renderizarAbaHoje() {
  const { hoje, horario, progresso, calendario, avaliacoes, privado } = ESTADO;
  document.getElementById("hoje-data-badge").textContent = `${hoje.dia_semana_nome} · ${hoje.data_br}`;

  const aulasHoje = (horario.aulas || [])
    .filter((a) => (a.dias || []).includes(hoje.dia_semana_cod))
    .sort((a, b) => a.inicio.localeCompare(b.inicio));

  const boxAulas = document.getElementById("hoje-aulas-box");
  if ((horario.sem_aula || []).includes(hoje.data)) {
    boxAulas.innerHTML = `<p><strong>Feriado / Recesso Acadêmico</strong> — Não há aulas presenciais hoje.</p>`;
  } else if (aulasHoje.length === 0) {
    boxAulas.innerHTML = `<p class="muted">Nenhuma aula presencial na grade hoje (${hoje.dia_semana_nome}).</p>`;
  } else {
    boxAulas.innerHTML = aulasHoje
      .map(
        (a) => `
      <div class="list-row">
        <div>
          <strong>${a.inicio}–${a.fim} · ${a.codigo} — ${a.nome}</strong>
          <div class="muted-sm">Prof. ${a.professor} · Sala: ${a.sala}</div>
        </div>
        <span class="tag tag-blue">Turma ${a.turma}</span>
      </div>`
      )
      .join("");
  }

  // Barras de Integralização
  const p = progresso;
  const itensProg = [
    {
      titulo: "Disciplinas Obrigatórias",
      feito: p.obrigatorias.concluidas,
      cursando: p.obrigatorias.cursando,
      meta: p.obrigatorias.meta,
      extra: `+${p.obrigatorias.cursando}h cursando`,
    },
    {
      titulo: "Disciplinas Optativas",
      feito: p.optativas.concluidas,
      cursando: p.optativas.cursando,
      meta: p.optativas.meta,
      extra: `+${p.optativas.cursando}h cursando`,
    },
    {
      titulo: "Atividades Formativas",
      feito: p.formativas.concluidas,
      cursando: 0,
      meta: p.formativas.meta,
      extra: "com tetos por categoria",
    },
    {
      titulo: "Extensão Universitária (ACE)",
      feito: p.extensao.concluidas,
      cursando: 0,
      meta: p.extensao.meta,
      extra: `ACE-IV: ${p.extensao.ace_iv}/${p.extensao.ace_iv_meta}h`,
    },
  ];

  document.getElementById("progresso-barras").innerHTML = itensProg
    .map((it) => {
      const pctFeito = Math.min(100, Math.round((it.feito / it.meta) * 100));
      const pctCursando = Math.min(100 - pctFeito, Math.round((it.cursando / it.meta) * 100));
      return `
      <div class="progress-item">
        <div class="progress-top">
          <strong>${it.titulo}</strong>
          <span><strong>${it.feito}/${it.meta}h (${pctFeito}%)</strong> <small class="muted">· ${it.extra}</small></span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width:${pctFeito}%"></div>
          <div class="progress-fill-cursando" style="width:${pctCursando}%"></div>
        </div>
      </div>`;
    })
    .join("");

  // Tabela de Horários Semanal
  const faixas = [
    { rotulo: "07:30–09:30", ini: "07:30" },
    { rotulo: "09:30–11:30", ini: "09:30" },
    { rotulo: "13:30–15:30", ini: "13:30" },
    { rotulo: "15:30–17:30", ini: "15:30" },
  ];
  const dias = ["seg", "ter", "qua", "qui", "sex"];
  const tbody = document.getElementById("tbody-horario");
  tbody.innerHTML = faixas
    .map((f) => {
      const cols = dias
        .map((d) => {
          const aula = (horario.aulas || []).find((a) => a.inicio === f.ini && (a.dias || []).includes(d));
          if (!aula) return `<td class="muted-sm">—</td>`;
          return `<td>
            <div class="aula-slot">
              <strong>${aula.codigo} · ${aula.nome}</strong>
              <small>Sala: ${aula.sala}</small>
              <small>${aula.professor}</small>
            </div>
          </td>`;
        })
        .join("");
      return `<tr><td><strong>${f.rotulo}</strong></td>${cols}</tr>`;
    })
    .join("");

  // Próximos 30 dias
  const prox = [];
  for (const ev of calendario || []) {
    const diffIni = diasEntre(ev.inicio, hoje.data);
    const diffFim = diasEntre(ev.fim, hoje.data);
    if (diffFim >= 0 && diffIni <= 30 && ev.tipo !== "feriado") {
      prox.push({
        inicio: ev.inicio,
        fim: ev.fim,
        titulo: ev.titulo,
        tipo: ev.tipo,
        obs: ev.obs || "",
      });
    }
  }
  for (const av of avaliacoes || []) {
    const diff = diasEntre(av.data, hoje.data);
    if (diff >= 0 && diff <= 30) {
      prox.push({
        inicio: av.data,
        fim: av.data,
        titulo: `[${av.codigo}] ${av.titulo}`,
        tipo: "avaliacao",
        obs: av.obs || "",
      });
    }
  }
  prox.sort((a, b) => a.inicio.localeCompare(b.inicio));

  const el30d = document.getElementById("lista-proximos-30d");
  if (prox.length === 0) {
    el30d.innerHTML = `<p class="muted">Nenhum prazo nos próximos 30 dias.</p>`;
  } else {
    el30d.innerHTML = prox
      .map((item) => {
        const dIni = diasEntre(item.inicio, hoje.data);
        const dFim = diasEntre(item.fim, hoje.data);
        let badge = "";
        if (dIni <= 0 && dFim >= 0) {
          badge = `<span class="tag tag-amber">Em andamento (${dFim === 0 ? "termina hoje" : `${dFim}d restantes`})</span>`;
        } else if (dIni === 1) {
          badge = `<span class="tag tag-red">Amanhã</span>`;
        } else {
          badge = `<span class="tag tag-blue">Em ${dIni}d</span>`;
        }
        const datas =
          item.inicio === item.fim
            ? formatarDataCurta(item.inicio)
            : `${formatarDataCurta(item.inicio)}–${formatarDataCurta(item.fim)}`;
        return `
        <div class="list-row">
          <div>
            <strong>${datas} · ${item.titulo}</strong>
            ${item.obs ? `<div class="muted-sm">${item.obs}</div>` : ""}
          </div>
          ${badge}
        </div>`;
      })
      .join("");
  }

  // Metas do Semestre
  const metas = (privado && privado.metas_semestre) || [];
  const feitas = metas.filter((m) => m.feita).length;
  document.getElementById("metas-contador").textContent = `${feitas}/${metas.length}`;
  document.getElementById("lista-metas-semestre").innerHTML = metas
    .map(
      (m, idx) => `
    <div class="checklist-item ${m.feita ? "done" : ""}">
      <label class="checkbox-label">
        <input type="checkbox" ${m.feita ? "checked" : ""} onchange="alternarMeta(${idx}, this.checked)">
        <span>${m.texto}</span>
      </label>
      <button class="btn btn-sm" onclick="removerMeta(${idx})" title="Remover">✕</button>
    </div>`
    )
    .join("");
}

async function confirmar1Semestre() {
  try {
    const res = await apiPost("/api/grade/confirmar-1sem");
    mostrarToast(`${res.confirmadas} disciplinas do 1º semestre confirmadas.`);
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

async function alternarMeta(idx, valor) {
  ESTADO.privado.metas_semestre[idx].feita = valor;
  await apiPost("/api/privado/salvar", { metas_semestre: ESTADO.privado.metas_semestre });
}

async function adicionarMeta() {
  const inp = document.getElementById("input-nova-meta");
  const txt = inp.value.trim();
  if (!txt) return;
  inp.value = "";
  ESTADO.privado.metas_semestre.push({ texto: txt, feita: false });
  await apiPost("/api/privado/salvar", { metas_semestre: ESTADO.privado.metas_semestre });
  mostrarToast("Meta adicionada.");
}

async function removerMeta(idx) {
  ESTADO.privado.metas_semestre.splice(idx, 1);
  await apiPost("/api/privado/salvar", { metas_semestre: ESTADO.privado.metas_semestre });
}

/* ==================== ABA 02: MINHAS MATÉRIAS (2026.2) ==================== */
function calcularSituacaoUFPR(notas) {
  const vals = [notas.p1, notas.p2, notas.p3, notas.trabalhos]
    .filter((v) => v !== null && v !== undefined && String(v).trim() !== "")
    .map((v) => parseFloat(String(v).replace(",", ".")));

  if (vals.length === 0) {
    return { texto: "∴ Insira suas notas (0–100 ou 0–10) para simular aprovação.", classe: "" };
  }
  const mediaBruta = vals.reduce((a, b) => a + b, 0) / vals.length;
  const escala10 = vals.every((v) => v <= 10);
  const media100 = escala10 ? mediaBruta * 10 : mediaBruta;

  if (media100 >= 70) {
    return {
      texto: `∴ Média Parcial: ${media100.toFixed(1)} / 100 — Aprovado direto por média (≥ 70).`,
      classe: "tag-green",
    };
  }
  if (media100 >= 40) {
    const precisaExame = Math.max(0, 100 - media100);
    if (notas.exame !== null && notas.exame !== undefined && String(notas.exame).trim() !== "") {
      let ex = parseFloat(String(notas.exame).replace(",", "."));
      if (escala10 && ex <= 10) ex *= 10;
      const mf = (media100 + ex) / 2;
      return {
        texto:
          mf >= 50
            ? `∴ Média Final pós-Exame: ${mf.toFixed(1)} / 100 — Aprovado no Exame Final.`
            : `Δ Média Final: ${mf.toFixed(1)} / 100 — Abaixo de 50 no Exame Final.`,
        classe: mf >= 50 ? "tag-green" : "tag-red",
      };
    }
    return {
      texto: `Δ Média Parcial: ${media100.toFixed(1)} / 100 — Exame Final: precisa tirar ${precisaExame.toFixed(1)} / 100 (ou ${(precisaExame / 10).toFixed(1)}) no exame.`,
      classe: "tag-amber",
    };
  }
  return {
    texto: `Δ Média Parcial: ${media100.toFixed(1)} / 100 — Abaixo de 40 (precisa subir para ≥ 40 para ter direito a exame).`,
    classe: "tag-red",
  };
}

function renderizarAbaDisciplinas() {
  const { horario, privado, disciplinas_info, avaliacoes } = ESTADO;
  const cont = document.getElementById("cards-disciplinas-atuais");
  const aulas = horario.aulas || [];
  const privDisc = (privado && privado.disciplinas) || {};

  cont.innerHTML = aulas
    .map((a) => {
      const cod = a.codigo;
      const dPriv = privDisc[cod] || {
        p1: "",
        p2: "",
        p3: "",
        trabalhos: "",
        exame: "",
        faltas_horas: 0,
        link_virtual: "",
        notas_rapidas: "",
      };
      const info = disciplinas_info[cod] || {};
      const chTotal = 60;
      const maxFaltasH = chTotal * 0.25; // 15h
      const faltasH = Number(dPriv.faltas_horas || 0);
      const pctFaltas = Math.min(100, Math.round((faltasH / maxFaltasH) * 100));
      const calc = calcularSituacaoUFPR(dPriv);
      const provasDisc = (avaliacoes || []).filter((av) => av.codigo === cod);

      return `
      <div class="disc-card" data-codigo="${cod}">
        <div class="card-header" style="margin-bottom:4px">
          <div>
            <h3>${cod} — ${a.nome}</h3>
            <span class="muted-sm">${a.dias.join(", ").toUpperCase()} · ${a.inicio}–${a.fim} · Turma ${a.turma}</span>
          </div>
          <span class="tag ${a.obs === "eletiva" ? "tag-amber" : "tag-blue"}">${a.obs === "eletiva" ? "ELETIVA · 60h" : "60h"}</span>
        </div>

        <div class="form-row">
          <div class="form-field">
            <label>PROFESSOR(A)</label>
            <input type="text" id="prof-${cod}" value="${a.professor || ""}" onchange="salvarHorarioDisciplina('${cod}')">
          </div>
          <div class="form-field">
            <label>SALA / ENSALAMENTO</label>
            <input type="text" id="sala-${cod}" value="${a.sala || ""}" onchange="salvarHorarioDisciplina('${cod}')">
          </div>
        </div>

        <div>
          <label style="font-family:var(--font-mono);font-size:0.72rem;font-weight:600;color:var(--muted);display:block;margin-bottom:6px">NOTAS PARCIAIS &amp; SIMULADOR UFPR</label>
          <div class="disc-notas-grid">
            <div><label>P1</label><input type="text" data-campo="p1" value="${dPriv.p1 ?? ""}" oninput="atualizarNotaLocal('${cod}', 'p1', this.value)"></div>
            <div><label>P2</label><input type="text" data-campo="p2" value="${dPriv.p2 ?? ""}" oninput="atualizarNotaLocal('${cod}', 'p2', this.value)"></div>
            <div><label>P3</label><input type="text" data-campo="p3" value="${dPriv.p3 ?? ""}" oninput="atualizarNotaLocal('${cod}', 'p3', this.value)"></div>
            <div><label>TRAB</label><input type="text" data-campo="trabalhos" value="${dPriv.trabalhos ?? ""}" oninput="atualizarNotaLocal('${cod}', 'trabalhos', this.value)"></div>
            <div><label>EXAME</label><input type="text" data-campo="exame" value="${dPriv.exame ?? ""}" oninput="atualizarNotaLocal('${cod}', 'exame', this.value)"></div>
          </div>
          <div class="calc-resultado" id="calc-${cod}" style="margin-top:8px">${calc.texto}</div>
        </div>

        <div class="faltas-bar">
          <div>
            <strong>Faltas: ${faltasH}h / ${maxFaltasH}h máx (25%)</strong>
            <div class="muted-sm">Restam ${Math.max(0, Math.floor((maxFaltasH - faltasH) / 2))} aula(s) de 2h dentro do limite</div>
          </div>
          <div style="display:flex;gap:6px">
            <button class="btn btn-sm" onclick="ajustarFalta('${cod}', -2)">−2h</button>
            <button class="btn btn-sm ${pctFaltas >= 80 ? "btn-danger" : ""}" onclick="ajustarFalta('${cod}', 2)">+2h</button>
          </div>
        </div>

        <div class="form-field">
          <label>CRITÉRIO DE AVALIAÇÃO / ANOTAÇÕES</label>
          <input type="text" value="${(dPriv.notas_rapidas || "").replace(/"/g, "&quot;")}" placeholder="Ex: Média = 0.4*P1 + 0.4*P2 + 0.2*Listas" oninput="atualizarNotaLocal('${cod}', 'notas_rapidas', this.value)">
        </div>

        ${
          provasDisc.length > 0
            ? `<div class="muted-sm"><strong>Próximas avaliações:</strong> ${provasDisc
                .map((p) => `${formatarDataCurta(p.data)} (${p.titulo})`)
                .join(" · ")}</div>`
            : ""
        }

        ${
          info.ementa
            ? `<details class="muted-sm">
                <summary style="cursor:pointer;font-weight:600">Ementa &amp; Bibliografia (${info.pasta})</summary>
                <p style="margin:6px 0">${info.ementa}</p>
                ${
                  info.bibliografia && info.bibliografia.length
                    ? `<ul>${info.bibliografia.map((b) => `<li>${b}</li>`).join("")}</ul>`
                    : ""
                }
              </details>`
            : ""
        }
      </div>`;
    })
    .join("");
}

function atualizarNotaLocal(cod, campo, valor) {
  if (!ESTADO.privado.disciplinas[cod]) {
    ESTADO.privado.disciplinas[cod] = { p1: null, p2: null, p3: null, trabalhos: null, exame: null, faltas_horas: 0 };
  }
  ESTADO.privado.disciplinas[cod][campo] = valor === "" ? null : valor;
  const calc = calcularSituacaoUFPR(ESTADO.privado.disciplinas[cod]);
  const el = document.getElementById(`calc-${cod}`);
  if (el) el.textContent = calc.texto;
}

async function ajustarFalta(cod, deltaHoras) {
  if (!ESTADO.privado.disciplinas[cod]) {
    ESTADO.privado.disciplinas[cod] = { faltas_horas: 0 };
  }
  const atual = Number(ESTADO.privado.disciplinas[cod].faltas_horas || 0);
  ESTADO.privado.disciplinas[cod].faltas_horas = Math.max(0, atual + deltaHoras);
  await salvarDadosPrivados();
}

async function salvarDadosPrivados() {
  try {
    await apiPost("/api/privado/salvar", { disciplinas: ESTADO.privado.disciplinas });
    mostrarToast("Notas e faltas salvas em privado/historico.yml.");
  } catch (e) {
    mostrarToast("Erro ao salvar: " + e.message);
  }
}

async function salvarHorarioDisciplina(cod) {
  const prof = document.getElementById(`prof-${cod}`).value.trim();
  const sala = document.getElementById(`sala-${cod}`).value.trim();
  try {
    await apiPost("/api/horario/atualizar", { codigo: cod, professor: prof, sala: sala });
    mostrarToast(`${cod} atualizado em dados/horario-2026-2.yml.`);
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

/* ==================== ABA 03: GRADE CURRICULAR & PLANEJADOR ==================== */
function filtrarGrade(filtro, btn) {
  FILTRO_GRADE = filtro;
  document.querySelectorAll("[data-fgrade]").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderizarAbaGrade();
}

function renderizarAbaGrade() {
  const { grade, privado } = ESTADO;
  const plano = (privado && privado.plano_proximo_semestre) || [];

  const mapaDisc = {};
  Object.values(grade.semestres || {}).forEach((lista) =>
    lista.forEach((d) => {
      mapaDisc[d.codigo] = d;
    })
  );
  (grade.optativas_planejadas || []).forEach((o) => {
    mapaDisc[o.codigo] = { ...o, ch: o.ch || 60 };
  });

  const chPlanejada = plano.reduce((acc, c) => acc + ((mapaDisc[c] && mapaDisc[c].ch) || 60), 0);
  document.getElementById("planner-ch-total").textContent = `${chPlanejada}h (${Math.round(chPlanejada / 15)} créditos/sem)`;
  document.getElementById("planner-qtd").textContent = `${plano.length} disciplina(s)`;

  const chipsEl = document.getElementById("planner-chips");
  if (plano.length === 0) {
    chipsEl.innerHTML = `<span class="muted-sm">Nenhuma disciplina selecionada para 2027.1.</span>`;
  } else {
    chipsEl.innerHTML = plano
      .map((cod) => {
        const d = mapaDisc[cod] || { nome: cod, ch: 60 };
        return `<span class="tag tag-blue" style="gap:6px">
          <strong>${cod}</strong> · ${d.nome} (${d.ch}h)
          <button class="btn-close" style="font-size:0.8rem" onclick="alternarPlanoSemestre('${cod}')">✕</button>
        </span>`;
      })
      .join("");
  }

  // Semestres 1 a 8
  const contSem = document.getElementById("mapa-semestres");
  contSem.innerHTML = Object.entries(grade.semestres || {})
    .map(([numSem, lista]) => {
      const filtradas = lista.filter((d) => {
        if (FILTRO_GRADE === "todas") return true;
        if (FILTRO_GRADE === "cursando") return d.status === "cursando";
        if (FILTRO_GRADE === "concluida") return d.status === "concluida" || d.status === "dispensada";
        if (FILTRO_GRADE === "liberadas") return d.status === "pendente" && d.prereq_liberado;
        if (FILTRO_GRADE === "travadas") return d.status === "pendente" && !d.prereq_liberado;
        return true;
      });

      const chSem = lista.reduce((s, d) => s + d.ch, 0);
      return `
      <div class="semestre-col">
        <h3><span>0${numSem} · ${numSem}º Período</span> <span class="muted-sm">${chSem}h</span></h3>
        ${
          filtradas.length === 0
            ? `<p class="muted-sm">Nenhuma disciplina neste filtro.</p>`
            : filtradas
                .map((d) => {
                  const classeLib = d.status === "pendente" ? (d.prereq_liberado ? "liberada" : "travada") : "";
                  const noPlano = plano.includes(d.codigo);
                  return `
                  <div class="grade-item status-${d.status} ${classeLib}">
                    <div class="grade-item-top">
                      <span>${d.codigo} — ${d.nome}</span>
                      <span>${d.ch}h</span>
                    </div>
                    <div class="muted-sm" style="margin-top:3px">
                      Depto: ${d.depto}
                      ${
                        d.prereq && d.prereq.length
                          ? d.prereq_liberado
                            ? ` · Pré-req OK (${d.prereq.join(", ")})`
                            : ` · Requer: ${d.prereq_faltando.join(", ")}`
                          : ""
                      }
                      ${d.confirmado === false ? ` · <em>Conferir SIGA</em>` : ""}
                      ${d.ementa ? ` · <a href="${d.ementa}" target="_blank" rel="noopener">Ementa PDF</a>` : ""}
                    </div>
                    <div class="grade-item-actions">
                      <select onchange="mudarStatusDisciplina('${d.codigo}', this.value)">
                        <option value="concluida" ${d.status === "concluida" ? "selected" : ""}>Concluída</option>
                        <option value="cursando" ${d.status === "cursando" ? "selected" : ""}>Cursando</option>
                        <option value="pendente" ${d.status === "pendente" ? "selected" : ""}>Pendente</option>
                        <option value="dispensada" ${d.status === "dispensada" ? "selected" : ""}>Dispensada</option>
                      </select>
                      ${
                        d.status === "pendente"
                          ? `<button class="btn btn-sm ${noPlano ? "btn-primary" : ""}" onclick="alternarPlanoSemestre('${d.codigo}')">
                              ${noPlano ? "Em 2027.1" : "+ 2027.1"}
                            </button>`
                          : ""
                      }
                    </div>
                  </div>`;
                })
                .join("")
        }
      </div>`;
    })
    .join("");

  // Optativas Planejadas
  document.getElementById("lista-optativas-grade").innerHTML = (grade.optativas_planejadas || [])
    .map(
      (o) => `
    <div class="list-row">
      <div>
        <strong>${o.codigo} — ${o.nome}</strong>
        <div class="muted-sm">Trilha: <strong>${o.trilha}</strong> ${o.obs ? `· ${o.obs}` : ""}</div>
      </div>
      <select class="btn btn-sm" onchange="mudarStatusDisciplina('${o.codigo}', this.value)">
        <option value="pendente" ${o.status === "pendente" ? "selected" : ""}>Pendente</option>
        <option value="cursando" ${o.status === "cursando" ? "selected" : ""}>Cursando</option>
        <option value="concluida" ${o.status === "concluida" ? "selected" : ""}>Concluída</option>
      </select>
    </div>`
    )
    .join("");

  // Eletivas & Extensão
  const htmlEletivas = (grade.eletivas || [])
    .map(
      (e) => `
    <div class="list-row">
      <div>
        <strong>[Eletiva] ${e.codigo} — ${e.nome} (${e.ch}h)</strong>
        <div class="muted-sm">Semestre ${e.semestre} · Conta até 60h como Atividade Formativa após aprovação</div>
      </div>
      <span class="tag ${e.status === "cursando" ? "tag-blue" : "tag-red"}">${e.status}</span>
    </div>`
    )
    .join("");

  const htmlExt = (grade.optativas_extensao || [])
    .map(
      (x) => `
    <div class="list-row">
      <div>
        <strong>[Extensão] ${x.codigo} — ${x.nome} (${x.ch}h)</strong>
        <div class="muted-sm">${x.ace ? `Modalidade ACE ${x.ace}` : "Confirmar modalidade ACE com a CAE"}</div>
      </div>
      <span class="tag">${x.ch}h ACE</span>
    </div>`
    )
    .join("");

  document.getElementById("lista-eletivas-extensao").innerHTML = htmlEletivas + htmlExt;
}

async function mudarStatusDisciplina(codigo, novoStatus) {
  try {
    await apiPost("/api/grade/atualizar", { codigo, status: novoStatus, confirmado: true });
    mostrarToast(`${codigo} atualizado para '${novoStatus}' em dados/grade.yml.`);
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

async function alternarPlanoSemestre(codigo) {
  const plano = ESTADO.privado.plano_proximo_semestre || [];
  const idx = plano.indexOf(codigo);
  if (idx >= 0) {
    plano.splice(idx, 1);
  } else {
    plano.push(codigo);
  }
  ESTADO.privado.plano_proximo_semestre = plano;
  await apiPost("/api/privado/salvar", { plano_proximo_semestre: plano });
}

/* ==================== ABA 04: PROVAS, TRABALHOS & CALENDÁRIO ==================== */
document.addEventListener("change", (ev) => {
  if (ev.target && ev.target.id === "av-codigo") {
    const wrap = document.getElementById("av-codigo-outro-wrap");
    wrap.classList.toggle("hidden", ev.target.value !== "OUTRA");
  }
});

async function adicionarAvaliacao(ev) {
  ev.preventDefault();
  const selCod = document.getElementById("av-codigo").value;
  const codigo = selCod === "OUTRA" ? document.getElementById("av-codigo-outro").value.trim() : selCod;
  const corpo = {
    codigo,
    tipo: document.getElementById("av-tipo").value,
    titulo: document.getElementById("av-titulo").value,
    data: document.getElementById("av-data").value,
    hora: document.getElementById("av-hora").value,
    alerta: document.getElementById("av-alerta").value,
    obs: document.getElementById("av-obs").value,
  };
  try {
    await apiPost("/api/avaliacoes/adicionar", corpo);
    document.getElementById("av-titulo").value = "";
    document.getElementById("av-obs").value = "";
    mostrarToast("Avaliação salva em dados/avaliacoes.yml.");
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

async function removerAvaliacao(idx) {
  try {
    await apiPost("/api/avaliacoes/remover", { indice: idx });
    mostrarToast("Avaliação removida.");
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

function filtrarCalendario(filtro, btn) {
  FILTRO_CALENDARIO = filtro;
  if (btn) {
    btn.parentElement.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
  }
  renderizarAbaAvaliacoes();
}

function renderizarAbaAvaliacoes() {
  const { avaliacoes, calendario, hoje } = ESTADO;
  document.getElementById("av-total-tag").textContent = `${(avaliacoes || []).length}`;

  const boxAv = document.getElementById("lista-avaliacoes-cadastradas");
  if (!avaliacoes || avaliacoes.length === 0) {
    boxAv.innerHTML = `<p class="muted">Nenhuma prova ou trabalho cadastrado em <code>dados/avaliacoes.yml</code>.</p>`;
  } else {
    boxAv.innerHTML = avaliacoes
      .map((av, idx) => {
        const diff = diasEntre(av.data, hoje.data);
        const tag =
          diff < 0
            ? `<span class="tag">Encerrada</span>`
            : diff === 0
            ? `<span class="tag tag-red">Hoje</span>`
            : `<span class="tag tag-blue">Em ${diff}d</span>`;
        return `
        <div class="list-row">
          <div>
            <strong>${formatarDataBR(av.data)} ${av.hora ? `às ${av.hora}` : ""} · [${av.codigo}] ${av.titulo}</strong>
            <div class="muted-sm">Tipo: ${av.tipo} ${av.obs ? `· ${av.obs}` : ""}</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            ${tag}
            <button class="btn btn-sm btn-danger" onclick="removerAvaliacao(${idx})">Remover</button>
          </div>
        </div>`;
      })
      .join("");
  }

  // Calendário PROGRAP
  const evs = (calendario || []).filter((e) => {
    if (FILTRO_CALENDARIO === "futuros") return diasEntre(e.fim, hoje.data) >= 0;
    if (FILTRO_CALENDARIO === "todos") return true;
    return e.tipo === FILTRO_CALENDARIO;
  });

  document.getElementById("tabela-calendario-ufpr").innerHTML = `
    <table class="schedule-table">
      <thead><tr><th>Período</th><th>Evento / Prazo Oficial</th><th>Categoria</th><th>Status</th></tr></thead>
      <tbody>
        ${evs
          .map((e) => {
            const dIni = diasEntre(e.inicio, hoje.data);
            const dFim = diasEntre(e.fim, hoje.data);
            let sit = "";
            if (dFim < 0) sit = `<span class="muted-sm">Encerrado</span>`;
            else if (dIni <= 0 && dFim >= 0) sit = `<span class="tag tag-amber">Em andamento (${dFim}d)</span>`;
            else sit = `<span class="tag tag-blue">Em ${dIni}d</span>`;
            const datas =
              e.inicio === e.fim
                ? formatarDataBR(e.inicio)
                : `${formatarDataCurta(e.inicio)} a ${formatarDataBR(e.fim)}`;
            return `<tr>
              <td><strong>${datas}</strong></td>
              <td>${e.titulo} ${e.obs ? `<div class="muted-sm">${e.obs}</div>` : ""}</td>
              <td><span class="tag">${e.tipo}</span></td>
              <td>${sit}</td>
            </tr>`;
          })
          .join("")}
      </tbody>
    </table>`;
}

/* ==================== ABA 05: FORMATIVAS & EXTENSÃO ==================== */
function atualizarCategoriasAtividade() {
  const conta = document.getElementById("at-conta").value;
  const sel = document.getElementById("at-categoria");
  if (!sel) return;
  if (conta === "formativa") {
    sel.innerHTML = Object.entries(NOMES_CATEGORIAS_FORMATIVAS)
      .map(([k, nome]) => `<option value="${k}">${nome}</option>`)
      .join("");
  } else {
    sel.innerHTML = Object.entries(NOMES_MODALIDADES_ACE)
      .map(([k, nome]) => `<option value="${k}">${nome}</option>`)
      .join("");
  }
}

async function adicionarAtividade(ev) {
  ev.preventDefault();
  const corpo = {
    titulo: document.getElementById("at-titulo").value,
    conta_como: document.getElementById("at-conta").value,
    categoria: document.getElementById("at-categoria").value,
    data: document.getElementById("at-data").value,
    horas: document.getElementById("at-horas").value,
    certificado: document.getElementById("at-certificado").checked,
    obs: document.getElementById("at-obs").value,
  };
  try {
    await apiPost("/api/atividades/adicionar", corpo);
    document.getElementById("at-titulo").value = "";
    document.getElementById("at-horas").value = "";
    document.getElementById("at-obs").value = "";
    mostrarToast("Atividade registrada em dados/atividades.yml.");
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

async function removerAtividade(idx) {
  try {
    await apiPost("/api/atividades/remover", { indice: idx });
    mostrarToast("Atividade removida.");
  } catch (e) {
    mostrarToast("Erro: " + e.message);
  }
}

function renderizarAbaAtividades() {
  const sel = document.getElementById("at-categoria");
  if (sel && sel.options.length === 0) atualizarCategoriasAtividade();

  const { atividades, progresso } = ESTADO;
  const listaEl = document.getElementById("lista-atividades-registradas");
  if (!atividades || atividades.length === 0) {
    listaEl.innerHTML = `<p class="muted">Nenhuma atividade registrada em <code>dados/atividades.yml</code>. A 17ª SIEPE (19 a 23/10) conta na categoria de Participação em Eventos.</p>`;
  } else {
    listaEl.innerHTML = atividades
      .map(
        (a, idx) => `
      <div class="list-row">
        <div>
          <strong>${a.titulo} (${a.horas}h)</strong>
          <div class="muted-sm">${formatarDataBR(a.data)} · ${a.conta_como.toUpperCase()} (${a.categoria}) · ${
          a.certificado ? "PDF arquivado" : "Pendente salvar PDF em privado/certificados/"
        }</div>
        </div>
        <button class="btn btn-sm btn-danger" onclick="removerAtividade(${idx})">Remover</button>
      </div>`
      )
      .join("");
  }

  // Categorias Formativas
  const f = progresso.formativas;
  document.getElementById("painel-categorias-formativas").innerHTML = Object.entries(f.limites || {})
    .map(([cat, lim]) => {
      const val = (f.por_categoria_validado && f.por_categoria_validado[cat]) || 0;
      const pct = Math.min(100, Math.round((val / lim) * 100));
      return `
      <div class="cat-box">
        <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px">
          <strong>${NOMES_CATEGORIAS_FORMATIVAS[cat] || cat}</strong>
          <span style="font-family:var(--font-mono)">${val}/${lim}h</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      </div>`;
    })
    .join("");

  // Modalidades ACE
  const ex = progresso.extensao;
  document.getElementById("painel-categorias-extensao").innerHTML = Object.entries(NOMES_MODALIDADES_ACE)
    .map(([mod, nome]) => {
      const val = (ex.por_ace && ex.por_ace[mod]) || 0;
      return `
      <div class="cat-box">
        <div style="display:flex;justify-content:space-between;font-size:0.82rem">
          <strong>${nome}</strong>
          <span class="tag ${mod === "ACE-IV" ? "tag-amber" : "tag-blue"}">${val}h</span>
        </div>
      </div>`;
    })
    .join("");
}

/* ==================== ABA 06: RADAR UFPR ==================== */
function renderizarRadar() {
  const { radar, fontes_radar } = ESTADO;
  const termo = (document.getElementById("busca-radar")?.value || "").toLowerCase();

  const filtrados = (radar || []).filter(
    (r) =>
      r.titulo.toLowerCase().includes(termo) ||
      (r.fonte || "").toLowerCase().includes(termo) ||
      (r.resumo || "").toLowerCase().includes(termo)
  );

  document.getElementById("lista-radar-noticias").innerHTML =
    filtrados.length === 0
      ? `<p class="muted">Nenhuma notícia encontrada para esse filtro.</p>`
      : filtrados
          .map(
            (r) => `
        <div class="list-row">
          <div>
            <a href="${r.link}" target="_blank" rel="noopener"><strong>${r.titulo}</strong></a>
            <div class="muted-sm" style="font-family:var(--font-mono)">${formatarDataBR(r.data)} · ${r.fonte}</div>
            ${r.resumo ? `<p class="muted-sm" style="margin:4px 0 0">${r.resumo}</p>` : ""}
          </div>
        </div>`
          )
          .join("");

  document.getElementById("lista-fontes-radar").innerHTML = (fontes_radar || [])
    .map(
      (f) => `
    <div class="list-row">
      <div>
        <a href="${f.pagina}" target="_blank" rel="noopener"><strong>${f.nome}</strong></a>
        <div class="muted-sm">Tipo: <code>${f.tipo}</code></div>
      </div>
      <span class="tag tag-green">ATIVO</span>
    </div>`
    )
    .join("");
}

/* ==================== MODAL DE SINCRONIZAÇÃO GITHUB ==================== */
function abrirModalSync() {
  const modal = document.getElementById("modal-sync");
  modal.classList.remove("hidden");
  const inpTok = document.getElementById("sync-gh-token");
  if (inpTok) inpTok.value = obterTokenGitHub();
  const mods = (ESTADO && ESTADO.git && ESTADO.git.modificados) || [];
  const box = document.getElementById("sync-arquivos-box");
  if (ESTADO && ESTADO.modo_estatico) {
    box.innerHTML = obterTokenGitHub()
      ? "Modo Nuvem Ativo: Token configurado. Suas edições já fazem commit direto na API do GitHub."
      : "Modo Nuvem: Cole seu GitHub Token acima para gravar alterações direto no repositório.";
  } else if (mods.length === 0) {
    box.innerHTML = "Nenhuma modificação pendente (repositório sincronizado).";
  } else {
    box.innerHTML = mods.map((m) => `<div>${m}</div>`).join("");
  }
}

function fecharModalSync() {
  document.getElementById("modal-sync").classList.add("hidden");
}

async function executarSyncGitHub() {
  const btn = document.getElementById("btn-confirmar-sync");
  const msg = document.getElementById("sync-commit-msg").value;
  btn.disabled = true;
  btn.textContent = "Sincronizando...";
  try {
    const res = await apiPost("/api/github/sincronizar", { mensagem: msg });
    mostrarToast(res.mensagem);
    fecharModalSync();
  } catch (e) {
    mostrarToast("Erro ao sincronizar: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Executar Commit & Push";
  }
}

window.addEventListener("DOMContentLoaded", carregarEstado);
