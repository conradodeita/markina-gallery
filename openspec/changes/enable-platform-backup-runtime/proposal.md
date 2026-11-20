# Proposal: Rotina de backup global em produção

## Why

O backup PostgreSQL cifrado já foi enviado ao Workspace, relido e restaurado em ensaio sintético. O proprietário escolheu a conta Workspace já conectada. A pasta antiga `Oracle-Production-Backups/Pick-your-Pic`, usada pelo timer compartilhado e com arquivos existentes, deve permanecer intacta. O novo destino global é `Oracle-Production-Backups/Pick-your-Pic Global`; `Oracle-Production-Backups/Pick-your-Pic Tenants` fica reservado para subpastas futuras por UUID, sem habilitar backup ou restauração lógica por tenant nesta change. O proprietário selecionou e autorizou a pasta global pelo app com o escopo `drive.file`; o vínculo protegido ainda está pendente.

## What Changes

- Criar um chamador interno de produção para backup global do banco e da configuração essencial aprovada, com execução agendada e disparo manual pelo operador.
- Autorizar a pasta global escolhida pelo proprietário por seletor de arquivos integrado ao app e manter somente o escopo `drive.file`; vincular seu ID por configuração protegida e manter a recuperação da chave offline conforme D16.
- Preparar `Pick-your-Pic Tenants` como raiz reservada para organização futura por UUID, sem implementar backup/restore lógico por tenant nem alterar o timer compartilhado.
- Preservar os bloqueios dos adapters locais. Cifrar antes do envio, registrar estados distintos de upload, verificação e recuperação e comprovar retorno em PostgreSQL isolado.
- Instalar e operar o runtime exclusivamente por canal protegido, com artefato do SHA exato da CI, inventário/fingerprint e comandos fixos; manter serviço, timer e destino desativados até os gates próprios de cada etapa. A ativação do timer exige cópia real verificada, recuperação isolada comprovada e aprovação específica.
- Limitar a implantação ao Pick-your-Pic, com aprovação própria por etapa. O plano não inclui ativar expurgo, recuperar um tenant isoladamente ou substituir o processo de arquivo de fotos.

## Capabilities

### New Capabilities

- `media-storage/platform-backup-runtime`: execução interna de backup global no servidor, custódia e vinculação do destino, disparo manual, verificação de cópia e recuperação em ambiente isolado.

### Modified Capabilities

## Impact

Seletor autenticado da pasta, chamador de backup, configuração protegida, instalação e operação protegidas do runtime, agendamento exclusivo da Markina e procedimentos de teste, recuperação e rollback. O Google Picker requer uma chave de navegador e o número do projeto Google Cloud; restringir a chave à origem oficial do app e às APIs necessárias. Não requer rota pública, migration, alteração de DNS ou ampliação do escopo OAuth.
