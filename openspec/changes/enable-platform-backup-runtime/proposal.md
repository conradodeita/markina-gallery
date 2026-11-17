# Proposal: Rotina de backup global em produção

## Why

O backup PostgreSQL cifrado já foi enviado ao Workspace, relido e restaurado em ensaio sintético. O proprietário escolheu a conta Workspace já conectada e a pasta privada `Pick-your-Pic Tenants`. A biblioteca atual e o agendador local recusam o ambiente de produção, de modo que cadastrar a pasta e a chave ainda não instala a rotina diária.

## What Changes

- Criar um chamador interno de produção para backup global do banco e da configuração essencial aprovada, com execução agendada e disparo manual pelo operador.
- Usar a pasta verificada e a conexão autorizada do proprietário com `drive.file`. Entregar a chave operacional e a referência do destino por configuração protegida e manter a recuperação da chave offline conforme D16.
- Preservar os bloqueios dos adapters locais. Cifrar antes do envio, registrar estados distintos de upload, verificação e recuperação e comprovar retorno em PostgreSQL isolado.
- Limitar a implantação ao Pick-your-Pic, com aprovação própria por etapa. O plano não inclui ativar expurgo, recuperar um tenant isoladamente ou substituir o processo de arquivo de fotos.

## Capabilities

### New Capabilities

- `media-storage/platform-backup-runtime`: execução interna de backup global no servidor, custódia e vinculação do destino, disparo manual, verificação de cópia e recuperação em ambiente isolado.

### Modified Capabilities

## Impact

Chamador de backup, configuração protegida, agendamento exclusivo da Markina e procedimentos de teste, recuperação e rollback. Não requer rota pública, migration, alteração de DNS ou troca de credenciais do Google.
