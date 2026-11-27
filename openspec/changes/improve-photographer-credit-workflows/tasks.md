# Tasks

## 1. Identidade e busca do proprietário

- [x] 1.1 Reconciliar e verificar o perfil já implementado em `add-photographer-signup-portal`/migration 0097: cadastro verificado preserva nome informado e e-mail no tenant. Reutilizar esses campos, sem nova coluna, aprovação manual, inferência ou backfill; testar nome/e-mail persistidos e legado sem nome. Evidência em `validation-journey.md` — teste de ativação automática e persistência passou em 06/11/2026.
- [x] 1.2 Implementar busca server-side owner-only por nome informado e e-mail administrativo, com paginação e resposta mínima. Verificar busca parcial, ordenação estável, ocultação de e-mail em identidade ambígua, limites e negação para fotógrafo, cliente e operador técnico. Evidência em `validation-journey.md` — 3 testes direcionados passaram em SQLite em 06/11/2026.
- [x] 1.3 Apresentar nome e e-mail disponível no autocomplete acessível a teclado e toque, com loading, vazio e erro distintos; verificar seleção abre saldo/histórico do tenant correto sem botão separado de busca. Evidência em `validation-journey.md` — 25 testes de UI em 2 arquivos, incluindo seleção por nome e regressões de teclado, vazio, erro e resultados atrasados, passaram em 06/11/2026.
- [x] 1.4 Acrescentar Todos, Ordem alfabética e Mais recentes à consulta owner-only, com estado inicial limpo, busca combinada por nome/e-mail, paginação server-side, desempate estável, limpeza de seleção e proteção contra resultados atrasados. Validar ordenação, carregamento incremental, vazio/erro, negação a não proprietário e apresentação em desktop/mobile. Evidência anterior em `validation-filters.md`: frontend 22/22, backend 6/6 SQLite e 5/5 PostgreSQL, página real com 14 tenants e paginação, seleção por toque, HTTP 403 de fotógrafo, build/lint/typecheck e OpenSpec strict. Esta evidência valida paginação e filtros por e-mail; o novo suporte de nome será provado nas tasks 1.1–1.3.

## 2. Carteira visível durante upload

- [x] 2.1 Exibir saldo disponível, reservas e estado por arquivo nos três fluxos de envio de conteúdo, usando leitura autenticada da carteira/operação; verificar consumo confirmado, liberação e conta ilimitada do proprietário sem débito fictício.
- [x] 2.2 Tratar timeout e confirmação ambígua como pendência até reconciliação, atualizando totais por resposta/leitura autorizada; verificar que a interface não antecipa nem duplica débito e preserva o aviso existente para JPEG repetido.
- [x] 2.3 Destacar o saldo disponível em formato compacto junto ao progresso do upload, mantendo reservas, estados por arquivo e a apresentação de carteira ilimitada. Em 27/11/2026, 69 testes de frontend, TypeScript e build passaram. Edge com PostgreSQL 17.11 sintético confirmou o saldo exibido após os dois envios (2→1 e 4→3) e o débito confirmado pelo servidor. O estilo de cartões foi substituído pela linha compartilhada de saldo.

## 3. Catálogo e cards de pacotes

- [x] 3.1 Disponibilizar catálogo somente de pacotes ativos a fotógrafo autenticado, aprovado e ativo, logo abaixo da carteira; verificar conta não ativada, tenant incorreto, lista vazia e falha de leitura sem confusão com saldo zero.
- [x] 3.2 Construir cards mobile-first com nome, descrição, quantidade, preço/moeda e estados interativos derivados do servidor; verificar responsividade, foco/teclado, toque, card e botão iniciando a mesma ação, conteúdo sem promoção inventada e `prefers-reduced-motion`. Evidência em `validation-journey.md`: card inteiro por clique e botão por Enter, foco/seleção/disabled, viewport390px sem overflow, movimento reduzido restaurado, 22 testes, lint/typecheck e build aprovados.
- [x] 3.3 Integrar ao checkout transparente atual, reutilizando Orders API e conta ativa configurada pelo proprietário, com tenant comprador e recebedor separados e Mercado Pago como único provedor padrão, sem PIX interno; verificar conta proprietária e preço server-side, isolamento, nenhum crédito antes da confirmação e política aprovada de bloqueio/revisão manual após estorno ou chargeback. Implementação e contratos em `../add-mercadopago-credit-purchases/validation.md`; UI real e nova Order sandbox em `validation-journey.md`. Limites externos do provedor permanecem explicitamente abertos na task 4.2 daquela change e não autorizam release.

## 4. Integração e revisão

- [x] 4.1 Validar os três fluxos juntos com tenants sintéticos, papéis distintos, upload parcial e catálogo configurado; verificar isolamento, erros e preservação da carteira ilimitada do proprietário. Evidência integrada em `validation-journey.md`: Order sandbox confirmada, 12 créditos recebidos, 6 consumidos nos três fluxos, falha liberada, duplicada cancelada/confirmada, retry/reindex/capa sem novo débito, proprietário ilimitado e consulta real owner-only com ledger persistente.
- [x] 4.2 Revisar código diretamente afetado por elementos substituídos, aplicar somente limpeza segura e executar testes direcionados, lint, typecheck e build aplicáveis; registrar evidência sem ampliar para refatoração geral.
- [x] 4.3 Executar OpenSpec strict, revisar o diff da change e fazer verificação visual autenticada local dos cards, busca e upload; registrar limitações de ambiente e gates externos sem declarar publicação. Evidência inicial em `validation-journey.md`: três uploads autenticados, consulta real do proprietário, cards desktop/mobile/teclado/movimento reduzido, 22 testes frontend, lint/typecheck/build, 80 testes backend SQLite e 3 PostgreSQL, strict e diff revisados. A suíte backend completa não foi repetida; isso permanece gate de release, junto aos limites externos. O checkpoint de 03/11 mantinha 1.1–1.3 abertas; o complemento de 06/11 abaixo as conclui localmente, sem liberar publicação pública/R14.

## 5. Histórico resumido por pasta — revisão de01/11/2026

- [x] 5.1 Preservar proveniência da pasta/galeria no evento de nova reserva usando o JSON existente; verificar tenant correto, retries, rename/removal e legado sem snapshot, sem migration nem reescrita do ledger. Implementado no evento reserved existente; teste sintético de reserva/retry/rename/remoção, recusa de proveniência cruzada e saldo preservado passou em SQLite(1teste,14,90s). Validação PostgreSQL conjunta permanece em5.4.
- [x] 5.2 Implementar projeção server-side de consumos por pasta e paginação de resumos/detalhes para fotógrafo e proprietário; verificar mais de30fotos, novos uploads, homônimas, compras separadas, limites, isolamento e totais iguais ao ledger. Evidência em validation-folder-history.md:5cenários SQLite e5PostgreSQL aprovados, incluindo36fotos, snapshot de paginação e compras individuais.
- [x] 5.3 Apresentar histórico compartilhado com referência, data/hora do último envio, quantidade de fotos e total, expansão e paginação acessíveis, preservando os estados loading/erro/vazio e operações financeiras individuais. Componente compartilhado credit-history com28testesfrontend aprovados, paginação20+16, snapshot, abort/resposta atrasada e detalhes por expansão. Typecheck e ESLint direcionado passaram; confirmação integrada/build permanece em5.4.
- [x] 5.4 Validar contratos SQLite/PostgreSQL, componentes, UI autenticada com o tenant persistente da jornada, lint/typecheck/build e OpenSpec; revisar diff e registrar evidência de saldo/ledger preservados, sem publicação. Evidência em validation-folder-history.md:594frontend/70arquivos,60backendPostgreSQL, lint/typecheck/build e UI autenticada desktop/mobile; sete IDs do ledger originais preservados e quatro resumos totalizando6créditos.

## 6. Interface habitual somente com resumos — revisão posterior de 01/11/2026

Esta decisão substitui a expansão visual validada na task 5.3; aquela evidência continua registrando o checkpoint anterior. APIs de investigação, ledger e proveniência permanecem preservados.

- [x] 6.1 Remover expansão e renderização por foto do componente compartilhado nas telas do proprietário e fotógrafo, mantendo os cinco dados aprovados, paginação dos resumos e um aviso único para legado sem pasta; remover somente código/estilos/testes da interação substituída. Componente e CSS simplificados; 29 testes focados, typecheck e ESLint passaram. Consultas internas e ledger não foram alterados.
- [x] 6.2 Validar metadados, pasta com 2.000 fotos sem lista individual, ausência de requisições de detalhes, isolamento entre seleções e estados de erro; executar lint/typecheck/build aplicáveis, conferir UI local e que o ledger original e a consulta interna de rastreabilidade permanecem disponíveis. Evidência em validation-folder-history.md: 29 testes relacionados, 7 testes finais do componente, typecheck/ESLint/build aprovados; duas telas autenticadas sem expansão; sete lançamentos e seis referências internas preservados, saldo 6.

## 7. Texto comercial do pagamento — revisão de 01/11/2026

- [x] 7.1 Retirar do catálogo a frase sobre o PIX interno, manter a informação positiva sobre Mercado Pago, conferir renderização local e executar a validação proporcional; preservar regras e fluxo de pagamento. Frase retirada; 7 testes existentes da página e ESLint passaram; UI autenticada confirmou texto positivo e ausência da frase. OpenSpec strict e diff--check aprovados.

### Matriz de rastreabilidade

| Requisito da spec | Tasks |
| --- | --- |
| Acompanhamento da carteira durante o envio | 2.1, 2.2, 4.1 |
| Perfil do fotógrafo pesquisável pelo proprietário | 1.1, 1.2 |
| Pesquisa de carteira autorizada | 1.2, 1.3, 4.1 |
| Catálogo de pacotes para fotógrafos aprovados | 3.1, 3.3 |
| Cards de pacote elegantes e dinâmicos | 3.2, 4.3 |
| Compra iniciada pelo pacote selecionado | 3.3,7.1 |
| Histórico de consumo agrupado por pasta | 5.1,5.2,5.3,5.4,6.1,6.2 |

### Evidências da etapa 2

- GET tenant-safe `/admin/photo-assets/{photo_id}/credit-operation` retorna somente o estado mínimo da operação e o snapshot da carteira autenticada, com `Cache-Control: private, no-store`; foto de outro tenant responde 404.
- O hook compartilhado `frontend/app/admin/credits/credit-upload-status.tsx` acompanha saldo/reservas, cada `PhotoAsset`, confirmação terminal e pendências em Imagens, no Acervo da cliente e na galeria privada. Após 60 leituras automáticas sem resolução, a interface mantém a pendência e oferece verificação manual.
- A interface exibe reserva e consumo/liberação somente com resposta server-side; conta ilimitada não apresenta débito finito. A confirmação existente para JPEG repetido permanece no helper comum de upload.
- Validação atualizada em 2026-11-01: a suíte frontend completa passou com 577 testes em 68 arquivos; os 88 testes direcionados de créditos e uploads também passaram, incluindo a galeria privada. A suíte backend de carteira passou com 25 testes e 1 teste PostgreSQL de concorrência pulado por indisponibilidade do serviço; Ruff direcionado, ESLint direcionado, `npx tsc --noEmit`, `npm run build`, `npm run lint` (0 erros; 36 avisos) e `git diff --check` passaram. A tentativa da suíte backend completa não coletou 64 módulos porque o Python ativo não tem o pacote `mercadopago==3.6.0` exigido pelo repositório; não há `.venv` local. A verificação visual autenticada permanece na task 4.3.
- Base verificada neste checkpoint: branch `feature/pickyourpic-saas-mainline`, `HEAD` e `origin/main` em `6af538ecd5c46da7691fa973c33869f263945a25`. A árvore local contém alterações preexistentes de outras frentes; foram preservadas e não houve commit, deploy, migration ou escrita remota.

### Evidências da etapa 3.1

- O GET autenticado `/admin/credits/packages` exige contexto administrativo de tenant ativo, nega a identidade global do proprietário e carteiras ilimitadas, e retorna somente pacotes ativos com preço e moeda; a resposta usa `Cache-Control: private, no-store`.
- O serviço de consulta de catálogo não recebe tenant nem conta do browser. O tenant da sessão é validado pela API, e os dados comerciais retornados vêm do pacote configurado pelo proprietário.
- Testes sintéticos verificam pacote ativo, filtro de pacote inativo, negação ao proprietário, tenant suspenso e tenant de sessão divergente. A UI distingue carregamento, lista vazia e erro e apresenta o catálogo imediatamente após o resumo da carteira.
- Validação direcionada da etapa: os testes de API de catálogo passaram dentro de `test_photographer_credits.py` (25 passaram; 1 teste PostgreSQL de concorrência foi pulado); os testes frontend de catálogo/carteira passaram na suíte completa (577 testes em 68 arquivos). `npx tsc --noEmit`, ESLint direcionado, Ruff direcionado, build frontend e `git diff --check` passaram. A suíte backend geral permanece sem validação por falha de coleta do ambiente Python descrita acima.

### Evidência histórica da pesquisa por e-mail — 03/11/2026

- Foi acrescentado o GET owner-only `/admin/platform/credit-tenants/search`, com mínimo de dois caracteres, limite validado de até vinte sugestões e resposta restrita a ID do tenant, estado, host e e-mail que correspondeu à busca.
- O seletor atual carrega sugestões server-side por e-mail enquanto o proprietário digita, sem botão de busca e sem carregar a lista global inteira; a seleção abre os detalhes existentes da carteira. Debounce, cancelamento de requisições, estados de erro/vazio e navegação por setas/Enter estão cobertos por testes.
- A busca parcial por e-mail e a interação do seletor estão incluídas nos 577 testes frontend aprovados; autorização/isolamento do endpoint são cobertos pela suíte backend focada de carteira.
- No checkpoint anterior à 0097 o perfil não persistia nome. Em 03/11, a prova local 0097 passou a preservar o nome informado e o console o pesquisa; ainda faltava ligar esse perfil ao autocomplete de créditos. Esta lacuna foi concluída localmente no registro de 06/11 abaixo. Nenhuma inferência de nome legado foi adicionada.

### Estado reconciliado em 01/11/2026

- A busca por nome continua subordinada aos gates R14-0–6 de `add-photographer-signup-portal`. O proprietário confirmou usar e-mail agora para os filtros da task 1.4, sem inferir nomes; tasks 1.1–1.3 não serão encerradas apenas com busca por e-mail.
- O checkout transparente foi implementado localmente em `add-mercadopago-credit-purchases`, com o proprietário aprovando bloqueio/revisão manual após estorno ou chargeback, sem débito automático. Credenciais de teste foram fornecidas por arquivo protegido fora do repositório. Foram executadas quatro Orders de teste, callbacks, replays e reembolsos em ambiente local; limites restantes constam em `../add-mercadopago-credit-purchases/external-validation-results.md`.
- Os cards e o botão de compra funcionaram no ensaio da página real autenticada com sessões sintéticas, em desktop e mobile. A conferência das tasks 3.2–3.3 deve preservar todos os critérios especificados, inclusive a ação do card inteiro e limites da validação externa; não considerar conclusão apenas por encontrar componente relacionado.
- A verificação visual da carteira e da visão do proprietário foi realizada com banco sintético e fontes locais em cópia temporária, preservando o Next preexistente em 3002. Isso não confirma visualmente todos os três fluxos de upload da task 4.3.
- O `.venv` local com o SDK fixado foi autorizado e criado. A regressão relacionada de Orders passou 46 testes/1 ignorado; a suíte backend ampla anterior teve falhas e erros, todos registrados na change de compras, e não foi declarada verde. Esses achados permanecem requisitos para o release final.
- A task 1.4 foi concluída e validada localmente por solicitação direta do proprietário, sem encerrar as pendências das demais tasks nem autorizar publicação. Evidência verificável em `validation-filters.md`.

### Verificação complementar — 06/11/2026

- A prova de cadastro automatizado passou (`test_automatic_signup_creates_finite_tenant_and_real_admin_session_without_owner_approval`): email verificado e MFA concluído ativam o tenant automaticamente e persistem o nome informado em `Tenant.photographer_name`, sem aprovação manual do proprietário.
- A busca do proprietário passou em 3 testes SQLite: correspondência parcial por nome/e-mail e resposta mínima, ordenação/fallback de legado e ocultação de e-mail ambíguo, e negação a fotógrafo, cliente e operador técnico.
- O autocomplete passou em 25 testes de UI em 2 arquivos, cobrindo seleção por nome e regressões de teclado, estados vazio/erro e respostas atrasadas. `tsc --noEmit` e ESLint direcionado passaram.
- Ruff direcionado e `openspec validate improve-photographer-credit-workflows --strict` passaram. A change não adiciona migration nem altera integrações externas ou produção.

### Revisão proporcional e limpeza

- A revisão limitou-se aos três fluxos de upload, página/catálogo de créditos, autocomplete owner-only e endpoints/serviços diretamente relacionados. Não foi identificada limpeza segura que pudesse ser aplicada sem ampliar o escopo ou misturar as alterações locais preexistentes; nenhuma refatoração geral foi feita.
- A task 4.2 cobre somente código e testes locais. A aprovação de Orders/conta recebedora não habilita credenciais, migration, transação, homologação ou deploy.

## Workflow follow-up

- Sincronizar specs principais e arquivar somente após implementação, evidências completas e revisão humana.
- Nenhuma task autoriza migration, provisionamento, ativação ou deploy em homologação/produção, configuração de credenciais reais ou compra financeira real.
