# Design: Execução interna do backup no servidor

## Context

A prova externa sintética de 17/11/2026 recuperou o conteúdo baixado do Drive. O adapter Workspace e o coordenador local existem, porém `_local_runtime` impede o uso dos adapters locais em produção. D15, D16 e a decisão D17 atualizada regem o escopo, retenção, custódia e destino da rotina.

## Goals / Non-Goals

Integrar um chamador explícito e exclusivo da Markina, preservar fonte e aplicações e permitir execução agendada e manual auditada. A primeira ativação não habilita expurgo, backup de arquivos de mídia, recuperação por tenant, mudança de dados em produção ou botões de administração pública.

## Decisions

- Configuração protegida em `/etc/pyp-backup`, diretório `0700` de root. `keyring.json` contém versão, UUID da instalação de backup, ID da chave ativa e versões AES-256. `destination.json` contém o vínculo da instalação com um UUID de destino e uma pasta Drive identificada por ID, com marca da instalação e escopo `drive.file`. O loader deve recusar dono, modo, path, ambiente, chave ou vínculo divergentes.
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

Sem migration. Preparar as credenciais separadas da aplicação. Ensaiar com origens e destinos descartáveis. Mostrar inventário, alvos, checksum, limites, método de desligamento e recuperação para aprovação do pacote exato. A primeira publicação instala apenas os recursos aprovados da Markina. A ativação efetiva ocorre em etapa própria. O desligamento do agendador preserva as cópias e recibos; não apaga dados.
