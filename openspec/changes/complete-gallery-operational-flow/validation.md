# Validação

## Tentativa visual local — 12/11/2026

- A aba local `http://127.0.0.1:3039/library/cart` e uma nova aba local em `/admin` mostraram somente `Internal Server Error`; um GET read-only à raiz também retornou HTTP 500.
- A API em `127.0.0.1:8000/health` respondeu HTTP 200 (`{"status":"ok","service":"api"}`). Os processos existentes eram Next.js local em `3039` e uma API sintética em `8000`; nenhum foi reiniciado, encerrado ou reconfigurado.
- O servidor de desenvolvimento continuou em HTTP 500. A leitura focal de `frontend/.next/dev/logs/next-development.log` confirmou erros repetidos de incompatibilidade entre módulos gerados/carregados pelo Next (`routeModule.ensureInstrumentation is not a function`, `ensureInstrumentationRegisteredWithDeferredSpans is not a function` e `getScriptNonceFromHeaders is not a function`). Nenhum processo do usuário foi reiniciado. A API sintética em `8000` continuou saudável.
- Não foram usados usuário/senha, OTP, dados de cliente ou qualquer serviço externo. Nenhuma conclusão visual foi inferida nesta primeira tentativa.
- `openspec validate complete-gallery-operational-flow --strict` informou que o delta de `gallery-sales/operational-gallery-interface` não pode ser arquivado automaticamente porque o requisito modificado `Resumo e responsáveis da galeria-mãe` já não existe com esse cabeçalho na spec consolidada. O change valida como artefato, mas o aviso de archive/supersession precisa de reconciliação antes de qualquer sync/archive; não tentei arquivar.

## Prévia local isolada — 12/11/2026

- Para manter o dev server `3039` intocado, servi em `127.0.0.1:3042` o build standalone local já existente. A embalagem standalone não continha os diretórios `.next/static` e `public`; as folhas CSS da página retornavam 404. Copiei os assets gerados para o pacote standalone local, confirmei as quatro folhas CSS em HTTP 200 e reiniciei somente o processo `3042` que eu havia iniciado.
- A captura de tela e a árvore de acessibilidade da página `/photographer-signup` em `3042` mostram o formulário estilizado, com cartão alinhado, campos em coluna e chamada principal destacada. A resposta HTML e as folhas CSS foram confirmadas sem submeter cadastro ou enviar dados. O build é uma prévia do snapshot local e não uma prova do conjunto integrado atual.
- As rotas `/admin` e `/admin/settings` responderam HTTP 200, mas não houve login. Portanto, a revisão visual autenticada de vendas, configurações e fluxo administrativo, em desktop e celular, continua pendente; a task 4.4 segue aberta. A medição móvel da tela pública de cadastro não substitui essa revisão.
- `3039` ainda responde HTTP 500 e não foi reiniciado. Para revisar as telas protegidas em execução real será necessário um dev server saudável no worktree e a sessão local autenticada disponível; até lá, não declarar a revisão visual completa.

## Reconciliação estrutural do delta OpenSpec — 12/11/2026

- O requisito `Resumo e responsáveis da galeria-mãe` não tem cabeçalho equivalente na spec consolidada, e a busca pelos comportamentos de resumo, capa, link não listado e ordenação não encontrou uma definição equivalente nas specs principais. Por isso ele foi reclassificado de `MODIFIED` para `ADDED`; o conteúdo não mudou e nenhuma spec principal foi sincronizada.
- `openspec validate complete-gallery-operational-flow --strict` passou depois da correção sem o aviso de arquivamento anterior. A mudança continua sem sync/archive por depender de revisão humana.
- A checagem complementar de 390 px na tela pública de cadastro está registrada em `../add-photographer-signup-portal/validation.md`; ela não valida a galeria autenticada e não fecha a task 4.4.

## Rechecagem dos serviços locais — 12/11/2026

- GET somente leitura: `3039` respondeu HTTP 500; `3042` respondeu HTTP 200; no servidor isolado `3044`, `/photographer-signup`, `/admin/galleries` e `/admin/settings` responderam HTTP 200; as APIs sintéticas em `8000` e `8001` responderam HTTP 200.
- O processo `3039` começou às 11:08; o pacote instalado `next` foi modificado às 12:18 e está em `16.4.6`, enquanto `package-lock.json` fixa `16.4.2`. O log `.next/dev/logs/next-development.log` confirma erros repetidos de incompatibilidade entre módulos carregados/gerados. A sequência de horários é compatível com substituição das dependências enquanto o servidor rodava, mas não prova a causa inicial. O processo `3039`, o cache e as dependências do repositório não foram alterados.
- A rota administrativa em `3044` renderizou no navegador a mensagem de acesso negado; não havia sessão autenticada disponível. O `3044` usa cópia isolada do frontend e dependências instaladas conforme o lockfile, sem `.env` ou cache `.next` compartilhado. A revisão autenticada de vendas, configurações e fluxo da galeria continua pendente; a task 4.4 não está concluída. A revisão visual de signup em `3042` é complementar e não a substitui.

## Revalidação frontend reproduzível — 12/11/2026

- Uma cópia isolada do frontend recebeu `npm ci --no-audit --no-fund`, usando o `package-lock.json` existente (`next` 16.4.2); nenhum pacote do worktree foi reinstalado ou alterado. A API usada nos requests locais era a sintética em `8001`.
- A primeira execução completa concorrente terminou com 702/706 aprovados e quatro falhas: um teste de identidade não encontrou os arquivos Compose porque a cópia inicial incluía somente o frontend; três falhas/timeout de UI não se reproduziram isoladamente. Após incluir somente os dois Compose necessários na pasta temporária, os quatro testes focados passaram (128/128).
- A execução completa com `--maxWorkers=2` passou **706/706 em 88 arquivos**. Lint: **0 erros e 38 avisos**. `npx tsc --noEmit --pretty false`: exit 0. `npm run build`: compilação, TypeScript e geração das 27 páginas passaram.
- A instância de desenvolvimento isolada `3044` respondeu HTTP 200 em `/photographer-signup`, `/admin/galleries` e `/admin/settings`; o navegador mostrou que não havia sessão administrativa autenticada. Portanto, essa validação técnica não fecha a inspeção visual autenticada desktop/mobile exigida pela task 4.4.
- A execução de `npm run start` para servir o build após a geração foi bloqueada pelo controle automático de execução antes de iniciar processo. Nenhum processo adicional foi criado; não houve login, formulário, mudança de dados, envio externo ou acesso à produção.

## Revisão autenticada e correção integrada — 12/11/2026

- Após a manutenção autorizada do Docker, a sessão sintética continuou válida. Revisão em `3044`, API sintética em `8001`, banco tmpfs exclusivo `pyp-sales-review-20261111-01`. Nenhum dado de produção utilizado.
- Viewport 390x844: Configurações carrega checklist com 2/5 itens concluídos, checks de Termos/WhatsApp e link escolhido; seções recolhem/expandem; WhatsApp mostra sandbox. Termos continuam na última seção. Vendas carrega pedido sintético, comentário limitado abaixo do preço, favorito na miniatura, modal com navegação e fechamento. Editor amplia prévia e fecha por Escape. Resumo da galeria e estado vazio de pastas foram inspecionados. Navegações horizontais internas permanecem roláveis.
- Viewport 1366x900: resumo, pastas públicas, card de cliente/acervo expandido e editor inspecionados. No resumo, largura do documento 1351 px, sem overflow global. Em 390 px, Configurações apresentou largura de documento 375 px. Override de viewport restaurado após a revisão.
- A task 4.4 permanece aberta: esta inspeção é complementar, não substitui todos os cenários históricos nem o aceite visual humano registrado anteriormente. O possível desalinhamento no console global estreito ainda precisa de reprodução dedicada. Nenhuma spec principal foi sincronizada/arquivada.
- Achado financeiro: pedido sintético confirmado exibe ausência de comunicação na seção Pagamento. O seed cria SaleOrder confirmado sem PaymentCommunication, e o frontend usa ausência dessa relação para a mensagem. Não foi inferido erro financeiro de produção nem alterada regra de pagamento; falta validar a compatibilidade com históricos legítimos.
- Achado reproduzido: exclusão de pasta vazia com configuração persistida falhou em PostgreSQL com ForeignKeyViolation na FK composta de folder_processing_settings. A transação reverteu, preservando a pasta. A automação teve timeout durante a interação com a confirmação nativa; o código possui window.confirm, portanto não se conclui ausência de confirmação.
- Correção na autoridade sucessora `improve-gallery-and-client-data-lifecycle`, task R1: remover explicitamente a configuração do mesmo tenant antes da pasta, na mesma transação. Teste de regressão com guarda referencial reproduziu a falha antes da alteração; 13 testes de processamento e 9 casos focados de exclusão passaram em Linux na imagem CI já existente, com rede desligada e fontes somente leitura. Ruff e diff-check passaram. Não houve refatoração geral nem migration.
- PostgreSQL real sintético: limpeza/configuração e exclusão foram verificadas primeiro em transação revertida, com todas as impressões de conteúdo preservadas. Após recarregar somente a API local, um teste HTTP criou pasta descartável, confirmou configuração persistida, excluiu com 204 e verificou ausência de pasta/configuração e preservação da quantidade das configurações anteriores.
- Python Windows estava sem mercadopago; a versão 3.6.0 declarada em requirements foi instalada somente em `C:/codex-data/local-review/sales-review-20261111-01/runtime-packages`, sem alterar pacotes globais, .env ou credenciais. A API foi retomada pelo wrapper externo `resume_review_with_isolated_sdk.py`, PID observado 13300. Nenhum frontend foi reconstruído; a correção é exclusivamente backend.

### Limite estrutural do OpenSpec observado nesta revalidação

`openspec validate improve-gallery-and-client-data-lifecycle --strict` ainda aponta quatro warnings por requisitos históricos longos e informa que o arquivamento recusaria um MODIFIED cujo cabeçalho não existe na spec consolidada (`Configuração administrativa do modo de acesso e modelo herdado`). O cenário novo de regressão não foi apontado. Não declarar a change globalmente validada/arquivável; reconciliar esse delta com as decisões sucessoras antes de sync/archive. A task R1 foi validada tecnicamente, mas isto não fecha os demais gates históricos.

## Fechamento da revisão visual — 12/11/2026

- A limitação descrita em tentativas anteriores foi contornada sem reiniciar ou alterar o servidor `3039`: revisão autenticada em `3044`, com fotógrafo e dados sintéticos isolados. Configurações, Vendas e pagamentos, editor da galeria, cartão de cliente e pastas vazias foram verificados em 1366×900 e 390×844.
- No pedido sintético, comentário aparece abaixo do valor, o favorito permanece na miniatura e o estado de pagamento é coerente. No editor, a prévia ampliada está centralizada em 390×844 e Escape remove o modal da árvore de acessibilidade. A exclusão local da pasta vazia de teste foi repetida após a correção de FK; a UI confirmou sucesso e a lista ficou com cinco pastas.
- Achado visual pequeno em 390 px: “CSV financeiro detalhado” quebra em três linhas e a barra fixa de filtros ocupa bastante altura. O texto continua legível e não foi observado overflow global; fica registrado para refinamento posterior.
- Este registro posterior substitui os status pendentes das tentativas anteriores: task 4.4 foi concluída localmente. Nenhuma spec principal foi sincronizada/arquivada; não houve deploy, migration, commit, push ou acesso à produção.
- As capturas foram inspecionadas na saída visual do CUA, mas o fluxo não forneceu caminho para salvar PNGs no worktree. As observações da interface e da árvore de acessibilidade estão registradas aqui.
