# Conectando ao máximo com a UFPR

Este documento mapeia cada sistema da UFPR, mostra como outros estudantes se conectam a ele e explica o que este repositório já automatiza.

## Sistemas da UFPR

| Sistema | Para que serve | Login | Automação aqui |
|---|---|---|---|
| [Portal de Sistemas](https://sistemas.ufpr.br/) | login único (SSO Keycloak) para os demais sistemas | sua conta UFPR | — |
| [SIGA](https://siga.ufpr.br/) | matrícula, histórico, IC, relatórios, documentos | Portal de Sistemas | ❌ sem API pública (ver abaixo) |
| [UFPR Virtual](https://ufprvirtual.ufpr.br/) (Moodle) | aulas, tarefas, prazos das disciplinas | Portal de Sistemas | ✅ calendário assinável (passo 1) |
| [Moodle C3SL](https://moodle.c3sl.ufpr.br/) | algumas disciplinas do DINF (talvez CI185) | e-mail @inf.ufpr.br | ✅ mesmo processo do passo 1 |
| [Intranet](https://intranet.ufpr.br/) | e-mail @ufpr.br, submissão de resumos do EVINCI | sua conta UFPR | — |
| E-mail @ufpr.br | Office 365, GitHub Student Pack, avisos | — | ✅ recebe as Issues do radar (passo 3) |
| Sites WordPress (PROPG, PROGRAP, Exatas, CMAT, Mat. Industrial, portal) | notícias, editais, ofertas | público | ✅ **radar diário** (`dados/fontes.yml`) |
| [Calendário PROGRAP](https://prograp.ufpr.br/calendario-academico/) | prazos oficiais | público | ✅ convertido para `.ics` e monitorado |
| SEI | processos de estágio, requerimentos | via coordenação | — |
| [SIBI, bibliotecas](https://www.portal.ufpr.br/) | livros, Minha Biblioteca, periódicos CAPES | sua conta UFPR | — |

## Passo a passo

### 1. Prazos do UFPR Virtual no seu Google Calendar (5 minutos, sem código)

O Moodle costuma gerar um link de calendário pessoal que o Google Calendar consegue **assinar**, e então tarefas e questionários com prazo aparecem sozinhos. Ainda não confirmei a opção no UFPR Virtual; se ela não aparecer, a administração pode ter desligado.

1. Entre no [UFPR Virtual](https://ufprvirtual.ufpr.br/) → **Calendário** → **Importar ou exportar calendários** → **Exportar calendário**.
2. Escolha **Todos os cursos** e **Eventos recentes e próximos**, e clique em **Obter URL do calendário**.
3. No Google Calendar: **Outras agendas** → **+** → **Do URL** → cole o link.

⚠️ Esse link contém um **token pessoal**. **Não cole no repositório**, que é público. Se quiser guardar, use `privado/`.

### 2. Calendário acadêmico, aulas e provas deste repositório

Depois que o GitHub Pages estiver ativo, os links ficam em:
`https://holmgds-gui.github.io/mat.computacional-UFPR/`

- `calendario.ics`: tudo
- `prazos.ics`: prazos, eventos e provas
- `aulas.ics`: grade horária

Assine pelo mesmo caminho do passo 1 (**Do URL**). O Google atualiza agendas assinadas a cada **12 a 24 horas**, então mudanças não aparecem na hora.

### 3. Avisos por e-mail

As Issues abertas pelo radar e pelos lembretes geram notificação do GitHub. Em **github.com → Settings → Notifications**, deixe **Email** marcado para *Issues* dos repositórios que você acompanha. Também vale instalar o app GitHub Mobile.

### 4. Apps oficiais

- **UFPR Virtual**: app [Android](https://play.google.com/store/apps/details?id=br.ufpr.ufprvirtual) ou o app oficial **Moodle** no iOS, com o endereço `ufprvirtual.ufpr.br`. Recebe notificações de tarefas.

## Como outros estudantes fazem

Levantamento no GitHub em 10/2026:

| Projeto | O que faz | Lição |
|---|---|---|
| [PETComputacaoUFPR/calouros](https://github.com/PETComputacaoUFPR/calouros) | manual do calouro (contas, e-mail, Moodle, SIGA) | a base de "onde está cada coisa" |
| [ghlps/ru-menu-scraper](https://github.com/ghlps/ru-menu-scraper), [saadbruno/cardapio-ru-ufpr](https://github.com/saadbruno/cardapio-ru-ufpr), [j-armenio/RU_TwitterBot](https://github.com/j-armenio/RU_TwitterBot) | raspam o cardápio do RU e enviam por bot | scraping de páginas públicas é o padrão |
| [PET-Eletrica-UFPR/muralV3](https://github.com/PET-Eletrica-UFPR/muralV3) | mural com cardápio e avisos | painel agregador, como o do README |
| [CaioCastro1/usp-mcp](https://github.com/CaioCastro1/usp-mcp) (USP) | integra o Moodle via API do app móvel | confirmou que o **UFPR Virtual tem a API mobile ligada** |
| [Fezer/tcc-poc](https://github.com/Fezer/tcc-poc) | TCC que consome endpoints internos do SIGA | o SIGA tem API interna, mas **só com autenticação institucional** |

## Limites honestos: o que não dá para automatizar (ainda)

- **SIGA:** não tem API pública, e qualquer acesso precisa do **seu login**. Uma automação que guardasse sua senha no GitHub Actions seria um risco de segurança, e provavelmente fere os termos de uso. O caminho seguro é um **script local**, rodado por você no seu computador, que abre o navegador para *você* fazer login e então baixa histórico e matrícula para `privado/`. Fica como fase 3.
- **Notas e frequência:** ficam no SIGA ou no UFPR Virtual. Copie para `privado/historico.yml`.
- **API do UFPR Virtual (tarefas como Issues):** possível pela API mobile, já que `enablemobilewebservice=1`. Como o login é por SSO, o token precisa ser gerado pelo fluxo do app (`admin/tool/mobile/launch.php`) com você logado. Fica como fase 2; o passo 1 já cobre os prazos.

## Fases

- [x] **Fase 1:** dados públicos, com calendário `.ics`, radar de editais, painel e lembretes
- [ ] **Fase 2:** UFPR Virtual via API (token como *secret* do repositório)
- [ ] **Fase 3:** script local de SIGA (login feito por você, dados em `privado/`)
- [ ] Extra: cardápio do RU no painel
