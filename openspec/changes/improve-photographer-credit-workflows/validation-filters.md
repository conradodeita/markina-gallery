# Validação da task 1.4 — filtros de fotógrafos (checkpoint histórico de 01/11/2026)

Data: 01/11/2026. Solicitação e confirmação do proprietário: usar e-mail nesta etapa, mantendo o nome dependente do cadastro aprovado. Implementação local; nenhuma migration, deploy ou alteração em produção.

Este registro descreve o estado observado naquele checkpoint. A persistência do nome e a busca atual por nome/e-mail foram validadas depois, em `validation-journey.md` (06/11/2026).

## Comportamento e evidência

| Requisito | Evidência | Estado |
|---|---|---|
| Estado inicial limpo | Página real em sessão owner sintética: select vazio, nenhuma sugestão e nenhuma requisição para credit-tenants/search antes da ação | Confirmado |
| Todos | Ensaio com 14 tenants sintéticos: 10 na primeira página, 4 na segunda, UUIDs únicos em ordem estável | Confirmado |
| Ordem alfabética | Query filter- combinada com alphabetical: 12 e-mails em duas páginas, ordenados sem diferenciar caixa | Confirmado |
| Mais recentes | Datas sintéticas distintas: primeiro resultado filter-11, o tenant mais novo do subconjunto, reiniciando a paginação | Confirmado |
| Busca combinada | Query opcional aplicada no servidor; mínimo de dois caracteres sem modo, ou seleção explícita de modo | Confirmado |
| Limpar | Modo, busca, sugestões e carteira selecionada voltam ao estado vazio | Confirmado |
| Seleção por toque | Abre carteira correta e fecha sugestões; modo escolhido permanece até nova ação | Confirmado |
| Autorização | API real com sessão de fotógrafo recusou listagem global em HTTP 403; testes de serviço cobrem cliente, fotógrafo, operador técnico e identidade desconhecida | Confirmado |
| Respostas atrasadas e falhas | Testes de componentes ignoram buscas/páginas antigas, preservam página já carregada em falha incremental e permitem repetir Carregar mais | Confirmado |
| Múltiplos administradores | Um resultado por tenant; row_number escolhe e-mail que corresponde à busca e a ordenação usa exatamente o e-mail exibido | Confirmado |
| Consulta mínima | Teste de SQL confirma ausência de leitura de ledger e operações de crédito na listagem | Confirmado |
| Nome do fotógrafo | Não existe campo persistido disponível nesta etapa; não houve inferência ou migration | Pendente de 1.1/portal R14, conforme decisão expressa |

## Testes e ferramentas

- Frontend de créditos: **22/22 testes aprovados**, incluindo 5 cenários novos de filtro/paginação/limpeza. ESLint dos componentes e TypeScript passaram.
- Backend SQLite temporário: **6/6 testes aprovados**, sendo 5 novos de consulta e 1 de compatibilidade da busca anterior.
- Backend PostgreSQL 17 isolado: **5/5 testes de consulta aprovados em 35,73 segundos**. Schemas sintéticos exclusivos; nenhum acesso à base produtiva.
- Ruff, compileall e whitespace dos arquivos relacionados passaram. `openspec validate improve-photographer-credit-workflows --strict` passou.
- Build Next.js dos fontes revisados em cópia temporária, com a mesma instalação de dependências, passou. Usou diretório de build próprio para preservar o Next preexistente no checkout (porta 3002).
- Ensaio visual/autorizado por sessões sintéticas na página real `/admin/credits`, API real com banco de teste, viewport desktop 1280×1000 e mobile 390×844 com toque. Sem transbordamento horizontal no mobile.
- Capturas fora do Git: `C:\codex-data\temp\pyp-mp-external-20261101\owner-filters-alphabetical-desktop.png`, `owner-filters-empty-desktop.png` e `owner-filters-mobile.png`.

## Compatibilidade e revisão proporcional

- A API antiga de listagem completa não foi alterada. O helper anterior `search_credit_tenants` permanece retornando lista e preserva o comportamento de busca sem filtro; o novo helper paginado retorna items/has_more.
- A alteração não modifica autenticação, associação de tenant, concessões/revogações, checkout ou ledger. A revisão de limpeza removeu somente resets de estado redundantes no seletor, já cobertos por closeSuggestions.
- O trabalho local preexistente permaneceu no checkout. Nenhum commit, push, merge, sincronização de spec principal ou arquivamento foi feito.

## Reconciliação da regressão geral — 10/11/2026

A execução Linux pausada havia registrado duas expectativas antigas de `test_tenant_credit_browse.py`: a resposta já inclui o nome persistido e a ordenação aprovada coloca ao final a identidade sem nome que possui mais de um administrador ativo, sem eleger nem revelar e-mail oculto. Os testes foram alinhados ao cenário normativo existente e reforçam que a busca por e-mail não o expõe quando a identidade é ambígua. Nenhum serviço, SQL de produção, saldo ou regra comercial mudou. Com `test_tenant_producers.py`, a repetição focal passou **12/12**, seis avisos conhecidos de lifespan, 157,14 s; Ruff focal aprovado. A suíte integral ainda deve terminar; não converter esta prova focal em CI geral verde.

Reconciliação documental de 10/11: a referência remanescente a MFA obrigatório no perfil pesquisável foi substituída por e-mail verificado e senha, conforme a decisão posterior já implementada no onboarding progressivo. Não introduz nova regra: TOTP segue opcional, exigido após ativação. Nenhuma aprovação manual, backfill ou novo fator foi acrescentado ao cadastro.
