# Design: Execução interna do backup no servidor

## Context

A prova externa sintética de 17/11/2026 recuperou o conteúdo baixado do Drive. O adapter Workspace e o coordenador local existem, porém `_local_runtime` impede o uso dos adapters locais em produção. D15, D16 e a decisão D17 atualizada regem o escopo, retenção, custódia e destino da rotina.

## Goals / Non-Goals

Integrar um chamador explícito e exclusivo da Markina, preservar fonte e aplicações e permitir execução agendada e manual auditada. A primeira ativação não habilita expurgo, backup de arquivos de mídia, recuperação por tenant, mudança de dados em produção ou botões de administração pública.

## Decisions

- O callback do Picker SHALL verificar a ação antes de ocultar a janela. Eventos intermediários, incluindo `loaded`, SHALL preservar a visibilidade; somente seleção (`PICKED`) ou cancelamento (`CANCEL`) encerram a janela. A falha relatada em 20/11/2026 (abre e fecha imediatamente) corresponde ao fechamento incondicional anterior à verificação da ação. A autenticação e o escopo OAuth permanecem os existentes.

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
