# Semestres

Índice cronológico. O material de cada disciplina fica em [`disciplinas/`](../disciplinas/).

| Semestre | Período | Disciplinas | CH |
|---|---|---|---|
| [2026-1](2026-1.md) | 1º | CI182, CMI011, CMI012, CMI013, CMI014 | 300h |
| [2026-2](2026-2.md) | 2º | CE009, CI185, CMI021, CMI022, CMI023 | 300h |

## Como começar um semestre novo

1. Baixe o PDF de ofertas no site da coordenação, em [Currículo](https://matind.ufpr.br/curriculo/). O radar avisa quando ele muda.
2. Crie `dados/horario-AAAA-S.yml`, copiando o do semestre anterior, e mude `semestre_atual` / `periodo_atual` em `dados/curso.yml`.
3. Mude o `status` das disciplinas em `dados/grade.yml` (`cursando` / `concluida`).
4. Crie as pastas com `python scripts/nova_disciplina.py CODIGO1 CODIGO2 ...`.
5. Crie `semestres/AAAA-S.md` copiando o anterior.
6. Quando sair o calendário acadêmico novo, crie `dados/calendario-AAAA.yml`.
