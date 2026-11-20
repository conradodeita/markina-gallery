# Design: Execução interna do backup no servidor

## Context

A prova externa sintética de 17/11/2026 recuperou o conteúdo baixado do Drive. O adapter Workspace e o coordenador local existem, porém `_local_runtime` impede o uso dos adapters locais em produção. D15, D16 e a decisão D17 atualizada regem o escopo, retenção, custódia e destino da rotina.

## Goals / Non-Goals

Integrar um chamador explícito e exclusivo da Markina, preservar fonte e aplicações e permitir execução agendada e manual auditada. A primeira ativação não habilita expurgo, backup de arquivos de mídia, recuperação por tenant, mudança de dados em produção ou botões de administração pública.

## Decisions

- O reteste após #395 manteve o sintoma. A fronteira identificada em código é `window.focus` → `useConsoleAccess.refresh` → `access=null`/nova `revision` → desmontagem de `ConsoleContent` e do seletor. O teste integrado SHALL exercitar o callback `PICKED` antes e durante uma revalidação positiva. O shell SHALL conservar a instância montada, mas `hidden` e `inert`, durante a consulta de capabilities; falha, recusa ou logout desmontam o conteúdo. A revisão de foco não substitui a instância quando o acesso continua autorizado. O seletor SHALL invalidar operações e callbacks no unmount e ocultar seu diálogo. A revalidação, autenticação no backend e o segundo step-up permanecem obrigatórios; não persistir token, senha ou TOTP fora do fluxo existente. O texto de backup sem fonte integrada é estático e não confirma recebimento ou persistência da candidata.
- O gate API/web SHALL revisar e fixar também os blobs exatos de `frontend/app/admin/platform/use-console-access.ts` e `console-link.tsx`, consumidores diretamente envolvidos na revalidação. Uma mudança posterior desses helpers sem atualizar os pins SHALL ser recusada, sem wildcard de frontend ou ampliação do escopo operacional.

- O callback do Picker SHALL verificar a ação antes de ocultar a janela. Eventos intermediários, incluindo `loaded`, SHALL preservar a visibilidade; seleção (`PICKED`) e cancelamento (`CANCEL`) encerram a janela. A ação terminal `ERROR` SHALL encerrar o diálogo e mostrar uma mensagem genérica e sanitizada, sem criar candidata nem enviar pedido de autorização. A falha relatada em 20/11/2026 (abre e fecha imediatamente) correspondia ao fechamento incondicional anterior à verificação da ação. A nova falha (diálogo fecha após o clique em `Selecionar`, sem atualizar o app) pode ser um `ERROR` ignorado silenciosamente; o evento real ainda não foi observado no browser. A autenticação e o escopo OAuth permanecem os existentes.

- Configuração protegida em `/etc/pyp-backup`, diretório `0700` de root. `keyring.json` contém versão, UUID da instalação de backup, ID da chave ativa e versões AES-256. `destination.json` contém o vínculo da instalação com um UUID de destino e a pasta global Drive identificada por ID, com marca da instalação e escopo `drive.file`. O loader deve recusar dono, modo, path, ambiente, chave ou vínculo divergentes.
- Organização do Drive: preservar `Oracle-Production-Backups/Pick-your-Pic` sem mover, renomear ou excluir arquivos, pois o timer compartilhado a utiliza. O chamador Pick-your-Pic aponta somente para `Oracle-Production-Backups/Pick-your-Pic Global`. `Oracle-Production-Backups/Pick-your-Pic Tenants` é apenas uma raiz reservada; não significa que backup/restauração lógica por tenant estejam implementados.
- A criação das pastas pelo conector Google Drive não concede acesso ao cliente OAuth da aplicação. Antes de vincular o novo destino, o proprietário deve selecionar a pasta `Pick-your-Pic Global` pelo seletor integrado ao app usando o escopo já consentido `drive.file`. O backend valida que a seleção é uma pasta própria, privada, dentro da raiz esperada, com autorização do app e capacidade de criar filhos. Não solicitar o escopo amplo `drive`.
- A API do Picker fica habilitada no projeto Google Cloud. Um arquivo root-only separado `/etc/pyp-google-drive/picker-config.json`, montado read-only somente na API, contém chave de navegador, número do projeto e ID da raiz autorizada. A chave deve restringir os referers à origem oficial do app e `https://docs.google.com/*`, e as APIs ao Picker e ao Drive.
- O token OAuth de acesso curto é emitido após autenticação do proprietário e fica somente em memória durante a seleção; refresh token e segredo OAuth nunca são enviados ao navegador nem registrados em logs. O endpoint verifica a pasta selecionada e retorna somente seu nome e ID. Um comando root-only atualiza o ID da pasta em `destination.json` mantendo `enabled=false`; a seleção não habilita o serviço.
- O comando de vínculo deve aceitar apenas a seleção owner-only mais recente registrada em auditoria, reatestar pela API se a pasta ainda é própria, autorizada, privada e filha da raiz configurada, e trocar atomicamente somente `parent_folder_id`. Recusa config habilitada, link/symlink, arquivo com hardlink e desvio de modo/owner.
- A cópia de recuperação da mesma chave fica em mídia removível separada da origem e da conta Drive. O ID da chave e os parâmetros de proveniência precisam acompanhar o recibo técnico por backup para selecionar a versão correta sem depender do host. Preparar a configuração não liga o serviço.
- O chamador de produção terá uma fronteira explícita, com identidade de instalação e fonte marcadas. Adapters de teste e recuperação continuam rejeitando produção. Usar processo interno agendável, sem porta publicada, com posse exclusiva do lock, recursos limitados e diretórios dedicados.
- O arquivo operacional usa cabeçalho autenticado v2 com o ID da chave. O formato v1 dos ensaios anteriores permanece legível pelo fluxo local. A recuperação do v2 usa somente o arquivo baixado, o recibo e o keyring offline; a origem não participa. Mudança da chave ativa no mesmo dia é uma divergência que exige reconciliação.
- Origem PostgreSQL validada por identidade, versão e schema, com coleta consistente e somente leitura. A lista de configurações essenciais e as credenciais permitidas devem ser específicas do projeto e revisadas antes de qualquer cópia real. Não acessar outros projetos ou volumes.
- Um serviço systemd exclusivo chama o mesmo executável no horário e na operação manual. O dump é produzido pelo cliente PostgreSQL no container já atestado. O processo da API troca o refresh token pelo acesso efêmero por uma chamada interna do operador. O segredo OAuth e o refresh token permanecem na API. A pasta é reatestada como privada antes do snapshot.
- Reutilizar empacotamento, autenticação criptográfica, catálogo durável e adapter Workspace adequados ao limite aprovado. Conferir pai, escopo, token efêmero, tamanho e SHA-256 antes de registrar cópia conferida. A ausência de chave, OAuth inválido ou ambiente divergente aborta antes de enviar dados.
- Recibos e estados distinguem geração, upload, leitura autenticada e restore comprovado. O disparo manual usa a mesma proteção e a mesma identidade da rotina. Para um ponto diário já concluído, o operador recebe o recibo existente. Pontos extras fora da agenda exigem desenho separado.

## Risks / Trade-offs

O servidor é compartilhado. Medir espaço e carga e impor limites antes da primeira cópia real. O arquivo cifrado contém o banco global. A indisponibilidade da conta Workspace ou da chave pode inviabilizar recuperação. O ensaio operacional deve comprovar acesso à cópia e à chave a partir de fora do host de origem.

## Migration Plan

Sem migration de banco. Preparar o arquivo separado de configuração do Picker. Publicar o app e o runtime com o agendamento desativado; depois autorizar a pasta pelo app, vincular seu ID pela ferramenta root-only e ensaiar o destino global com arquivo sintético, reler, comparar checksum e remover somente os artefatos criados pelo ensaio. Mostrar inventário, alvos, checksum, limites, método de desligamento e recuperação antes da primeira cópia real. A primeira cópia real e a ativação do timer permanecem uma etapa separada com aprovação específica. O desligamento do agendador preserva as cópias e recibos; não apaga dados.

## Decisão aprovada em 19/11/2026: montagem protegida somente na API

O proprietário aprovou estender a ponte existente para uma operação fixa do Picker. O candidato SHALL manter imagem e APP_VERSION ativos e adicionar exclusivamente o bind `/etc/pyp-google-drive/picker-config.json` para `/run/secrets/google-drive-picker-config.json`, read-only, sem criação de origem. O arquivo SHALL ser root:root 0400, regular e link único sob diretório 0700. A prova SHALL vincular metadados e conteúdo sem divulgar chave ou hash da chave em logs.

Inventário, aprovação por fingerprint, lock comum, journal durável, stop/rename/create, provas semânticas, preservação dos anteriores, publicação da base e recuperação por fase SHALL reutilizar o canal protegido. Web SHALL permanecer no mesmo ID, imagem, configuração e StartedAt; os serviços de terceiros SHALL permanecer idênticos. A recuperação SHALL atuar somente na API. A instalação do suporte exige CI do SHA exato e fluxo protegido; aprovação desta extensão não dispensa revisão de PR/merge.

## Complemento proposto: instalação e ensaio pelo canal protegido

Este complemento fecha a lacuna operacional encontrada após a autorização real de `Pick-your-Pic Global`. A implementação permanece pendente de revisão do proprietário. O escopo é executar os requisitos de instalação, vínculo e prova sintética já previstos nesta change. Não autoriza publicação, primeira cópia real, ativação do timer ou uso de dados de tenant.

### Fluxo protegido

- Um workflow `workflow_dispatch` executável somente a partir de `main` confere CI do SHA exato e prepara um inventário somente de leitura. O inventário compara identidade do host, SHA/release, API e PostgreSQL ativos, schema, saúde, espaço disponível, estado das unidades, configuração root-only e hashes de artefatos; expõe somente a impressão digital e os fatos operacionais necessários, sem segredos, tokens, chaves ou IDs do Drive.
- O comando remoto SHALL constar de uma lista explícita no forced-command SSH wrapper e estar vinculado ao script/artefato do SHA revisado. Nenhuma entrada SHALL aceitar comando, shell, caminho ou nome de serviço arbitrário. A etapa mutável exige impressão digital idêntica, host idêntico ao preflight e aprovação do ambiente protegido `production`; CI ou merge sozinhos não liberam a operação.
- O pacote SHALL ser montado no CI a partir do código do SHA aprovado e de um repositório de wheels Linux ARM64/Python 3.10 com dependências fixadas por hash. O instalador verifica SHA-256 antes de extrair e instala em diretório root-only versionado, preservando a versão anterior e um recibo de rollback. O processo não lê `.env` nem inclui credenciais no artefato.
- A instalação poderá colocar os arquivos de serviço e timer no caminho aprovado e executar `daemon-reload`, mas SHALL deixá-los desativados e parados. A operação não altera Compose, API/web, PostgreSQL, Nginx, schema, containers de terceiros, timer compartilhado, DNS ou firewall. `destination.json` permanece com `enabled=false`.

### Vínculo e ensaio sintético

- O vínculo ocorre em operação root-only fixa, depois de um evento owner-only de seleção com no máximo 15 minutos. O operador revalida a pasta via OAuth da aplicação, atualiza atomicamente somente `parent_folder_id`, registra recibo sanitizado e confirma novamente `enabled=false`. Janela expirada ou qualquer divergência aborta sem escrita.
- Uma operação fixa de ensaio usa conteúdo sintético em memória e um marcador único por execução. Antes de enviar, confirma o vínculo protegido, a validação da pasta e o estado desativado. Depois, relê o mesmo item, compara bytes/tamanho/SHA-256, exclui somente o ID retornado pela criação daquela execução e confirma ausência. O ID fica somente no processo/registro root-only e não vai para logs ou sumário.
- O ensaio não chama `pg_dump`, não lê tabelas, fotos, filas ou credenciais de clientes, não inicia o serviço/timer e não cria itens em `Pick-your-Pic Tenants`. Uma falha de limpeza mantém o estado do ensaio pendente para reconciliação, sem tentativa de exclusão por nome amplo ou de objetos de outra execução.
- A seleção owner-only tem validade operacional de 15 minutos; portanto, deve ser renovada pelo proprietário imediatamente antes da etapa de vínculo, após a instalação do runtime. Se a execução expirar, o sistema aborta e solicita nova seleção no console, sem ampliar o prazo.

### Evidência e retorno

- CI prova artefato, lock e scripts no SHA exato. Testes isolados cobrem recusa de impressão digital/host/SHA divergentes, metadados e permissões root-only, instalação com unidades inertes, seleção expirada, atomicidade do vínculo, releitura/soma de verificação, falha de limpeza e preservação de arquivos não criados pelo ensaio.
- Antes do passo mutável, a revisão humana recebe SHA/digest do artefato, impressão digital, serviços/containers/portas observados, impacto, rollback e estado das cópias. Instalação deixa o runtime pronto e inerte. Vínculo e ensaio ficam em operação distinta e exigem nova aprovação protegida. A primeira cópia real e timer seguem gate próprio.
- Retorno pré-backup restaura apenas o diretório versionado e arquivos de unidade do Pick-your-Pic após comprovar que não há processo em curso; preserva configuração, catálogo, chave, artefatos Drive e todos os recursos externos ao projeto.
