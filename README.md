# Matemática Industrial — UFPR

Repositório acadêmico da minha graduação em **Bacharelado em Matemática Industrial** na Universidade Federal do Paraná: disciplinas, calendário, provas, pesquisa, extensão, eventos e carreira em um só lugar, com automações que acompanham a UFPR por mim.

`Currículo 2025` · `Ingresso 2026-1` · `Centro Politécnico, Curitiba` · interesses: **otimização · ciência de dados · IA**

<!-- painel:inicio -->
<!-- Gerado por scripts/painel.py. Não edite à mão. -->

**Hoje:** 26/10/2026 (segunda) · semestre 2026-2 · 2º período

**Aulas de hoje:** 07:30 TT081 Administração de Empresas · 15:30 TT080 Economia de Engenharia

### ⏳ Próximos 30 dias

Nada no horizonte. 🌤️

### 📊 Integralização

| Componente | Progresso |
|---|---|
| Obrigatórias | `███░░░░░░░░░░░░░░░░░ 300/1920h (16%)` + 120h cursando |
| Optativas | `░░░░░░░░░░░░░░░░░░░░ 0/300h (0%)` + 180h cursando |
| Atividades formativas | `░░░░░░░░░░░░░░░░░░░░ 0/200h (0%)` |
| Extensão (ACE) | `░░░░░░░░░░░░░░░░░░░░ 0/242h (0%)` · ACE IV: 0/90h |

> ⚠️ Situação a conferir no SIGA: CI182, CMI011, CMI012, CMI013, CMI014. Depois, marque `confirmado: true` em `dados/grade.yml`.

### 📡 Últimas do radar

- 23/10 · [A Universidade encontra a sociedade: o papel da extensão na Siepe 2026](https://ufpr.br/a-universidade-encontra-a-sociedade-o-papel-da-extensao-na-siepe-2026/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_
- 22/10 · [Novidade na Siepe, Jornadas de Internacionalização promovem trocas sobre mobilidade acadêmica](https://ufpr.br/novidade-na-siepe-jornadas-de-internacionalizacao-promovem-trocas-sobre-mobilidade-academica/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_
- 21/10 · [Webinar sobre “Editoração Científica, Ciência Aberta e Inteligência Artificial” tem transmissão da UFPR TV](https://ufpr.br/webinar-sobre-editoracao-cientifica-ciencia-aberta-e-inteligencia-artificial-tem-transmissao-da-ufpr-tv/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_
- 20/10 · [Enfermagem UFPR oferece curso de extensão em primeiros socorros](https://ufpr.br/enfermagem-ufpr-oferece-curso-de-extensao-em-primeiros-socorros/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_
- 20/10 · [Primeiras experiências na pesquisa e na extensão marcam a 17ª Siepe da UFPR](https://ufpr.br/primeiras-experiencias-na-pesquisa-e-na-extensao-marcam-a-17a-siepe-da-ufpr/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_
- 20/10 · [Página atualizada: Laboratórios](https://matind.ufpr.br/laboratorios/) — _Coordenação de Matemática Industrial (páginas)_
- 19/10 · [Semana de Ensino, Pesquisa e Extensão da UFPR começa nesta segunda-feira (19); veja a programação](https://ufpr.br/semana-de-ensino-pesquisa-e-extensao-da-ufpr-comeca-nesta-segunda-feira-19-veja-a-programacao/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_
- 19/10 · [Siepe: Veja as novidades do Enec, maior evento de extensão e cultura da UFPR](https://ufpr.br/siepe-veja-as-novidades-do-enec-maior-evento-de-extensao-e-cultura-da-ufpr/) — _Portal UFPR (notícias gerais, extensão, SIEPE)_

<sub>Painel atualizado automaticamente em 26/10/2026.</sub>
<!-- painel:fim -->

---

## 🗂️ Estrutura

| Pasta | Conteúdo |
|---|---|
| [`disciplinas/`](disciplinas/) | uma pasta por disciplina: ficha, ementa, avaliações, `anotacoes/`, `listas/`, `provas/`, `codigo/` |
| [`semestres/`](semestres/) | índice por semestre: grade horária, metas, retrospectiva |
| [`pesquisa/`](pesquisa/) | iniciação científica: como funciona, orientadores, projetos |
| [`extensao/`](extensao/) | as 242h obrigatórias de extensão (ACE) |
| [`eventos/`](eventos/) | SIEPE, semanas acadêmicas, olimpíadas, certificados |
| [`estagio/`](estagio/) | regras da COE, documentos, vagas |
| [`carreira/`](carreira/) | pós-graduação × mercado, Lattes, ORCID, portfólio |
| [`integracoes/`](integracoes/) | **como este repositório se conecta à UFPR** (SIGA, UFPR Virtual, sites) |
| [`dados/`](dados/) | a "fonte da verdade" em YAML: grade, calendário, horários, provas, atividades, fontes do radar |
| [`scripts/`](scripts/) | automações em Python |
| [`templates/`](templates/) | modelos de anotação (Markdown) e de lista (LaTeX) |
| `privado/` | **só no seu computador** (no `.gitignore`): notas, histórico, certificados |

## 🤖 Automações

Todos os dias, às 06:00, o GitHub Actions ([`atualizar.yml`](.github/workflows/atualizar.yml)):

1. **Radar:** verifica PROPG (IC), PROGRAP, Setor de Exatas, coordenações de Matemática e Mat. Industrial, horários do DMAT e o portal da UFPR. Novidades relevantes viram **Issues** com o rótulo `radar`, e o GitHub manda e-mail.
2. **Painel:** atualiza o topo deste README com as aulas do dia, os prazos dos próximos 30 dias, a integralização do curso e as últimas do radar.
3. **Lembretes:** abre uma Issue `⏰` alguns dias antes de matrícula, ajustes, provas e trabalhos.
4. **Calendário:** gera arquivos `.ics` e publica no GitHub Pages para assinar no Google Calendar.
   - 📅 <https://holmgds-gui.github.io/mat.computacional-UFPR/>

### Cadastrar pelo celular

- **Prova ou trabalho:** [Nova Issue → 🧪 Nova prova / trabalho](https://github.com/holmgds-gui/mat.computacional-UFPR/issues/new?template=nova-avaliacao.yml)
- **Certificado de atividade:** [Nova Issue → 🏅 Nova atividade](https://github.com/holmgds-gui/mat.computacional-UFPR/issues/new?template=nova-atividade.yml)

O formulário é convertido em dados, entra no calendário e no painel, e a Issue fecha sozinha. Só funciona para Issues abertas por você.

### Rodar localmente

O robô faz commits todos os dias. **Antes de editar, sempre rode `git pull`**, senão o seu push será recusado.

```bash
pip install -r requirements.txt
python scripts/gerar_calendario.py      # gera site/*.ics
python scripts/painel.py                # atualiza o painel deste README
python scripts/radar.py --simular       # mostra o que o radar encontraria hoje
python scripts/nova_disciplina.py CMI031  # cria a pasta de uma disciplina nova
```

## 🔗 Links rápidos

| | |
|---|---|
| **Sistemas** | [Portal de Sistemas](https://sistemas.ufpr.br/) · [SIGA](https://siga.ufpr.br/) · [UFPR Virtual](https://ufprvirtual.ufpr.br/) · [Intranet](https://intranet.ufpr.br/) |
| **Curso** | [Site da coordenação](https://matind.ufpr.br/) · [Currículo e ofertas](https://matind.ufpr.br/curriculo/) · [Documentos](https://matind.ufpr.br/documentos/) · [Optativas](https://matind.ufpr.br/disciplinas-optativas/) · cmind@ufpr.br |
| **Regras** | [PPC 2025](https://matind.ufpr.br/wp-content/uploads/2026/03/PPC-2025-Ativo.pdf) · [Formativas](https://matind.ufpr.br/wp-content/uploads/2026/03/Formativas.pdf) · [Estágio](https://matind.ufpr.br/wp-content/uploads/2025/12/Regulamento-de-Estagio-CMIND.pdf) |
| **Calendário** | [PROGRAP — calendário acadêmico](https://prograp.ufpr.br/calendario-academico/) |
| **Pesquisa** | [IC/PROPG](https://ufpr.br/propg/ict/) · [SIEPE](https://siepe.ufpr.br/) · [PPGM](https://ppgm.ufpr.br/portal/) |
| **Departamento** | [DMAT](https://mat.ufpr.br/) · [Horários das turmas](https://mat.ufpr.br/departamento/Aulas/Aulas_2026-2.html) |

## 🔒 Privacidade

O repositório é **público**. Notas, histórico, CPF, certificados e qualquer link com token ficam em `privado/`, que nunca é enviado. Para publicar algo dessa pasta, mova o arquivo para fora dela de propósito.
