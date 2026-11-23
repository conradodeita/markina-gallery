# Proposal: Rotina de backup global em produção

## Why

O backup PostgreSQL cifrado já foi enviado ao Workspace, relido e restaurado em ensaio sintético. O proprietário escolheu a conta Workspace já conectada. A pasta antiga `Oracle-Production-Backups/Pick-your-Pic`, usada pelo timer compartilhado e com arquivos existentes, deve permanecer intacta. O novo destino global é `Oracle-Production-Backups/Pick-your-Pic Global`; `Oracle-Production-Backups/Pick-your-Pic Tenants` fica reservado para subpastas futuras por UUID, sem habilitar backup ou restauração lógica por tenant nesta change. O proprietário selecionou e autorizou a pasta global pelo app com o escopo `drive.file`; o vínculo protegido ainda está pendente.

## What Changes

- Criar um chamador interno de produção para backup global do banco e da configuração essencial aprovada, com execução agendada e disparo manual pelo operador.
- Autorizar a pasta global escolhida pelo proprietário por seletor de arquivos integrado ao app e manter somente o escopo `drive.file`; vincular seu ID por configuração protegida e manter a recuperação da chave offline conforme D16.
- Preparar `Pick-your-Pic Tenants` como raiz reservada para organização futura por UUID, sem implementar backup/restore lógico por tenant nem alterar o timer compartilhado.
- Preservar os bloqueios dos adapters locais. Cifrar antes do envio, registrar estados distintos de upload, verificação e recuperação e comprovar retorno em PostgreSQL isolado.
- Instalar e operar o runtime exclusivamente por canal protegido, com artefato do SHA exato da CI, inventário/fingerprint e comandos fixos; manter serviço, timer e destino desativados até os gates próprios de cada etapa. A ativação do timer exige cópia real verificada, recuperação isolada comprovada e aprovação específica.
- Após uma instalação de wrapper declarada bem-sucedida, oferecer uma operação protegida e fixa de restauração pós-instalação: selecionar uma cópia anterior somente pelo SHA-256 registrado em recibo, validar CI da `main` no SHA exato, fingerprint e aprovação do ambiente protegido, preservar a versão ativa antes da troca atômica e comprovar metadados, hash, sintaxe, allowlist e invariância dos containers. Se a validação posterior à troca falhar, restaurar atomicamente a versão ativa antes da tentativa. Se essa recuperação compensatória falhar ou não puder ser comprovada, o fluxo SHALL interromper novas tentativas e alterações, preservar as versões e recibos envolvidos, marcar o wrapper ativo como não verificado e emitir somente diagnóstico estático sanitizado. Qualquer recuperação manual exige fluxo protegido próprio, revisado e mergeado com autorização, CI verde da `main` no SHA exato, preflight somente leitura atual, fingerprint revisada e aprovação operacional explícita para o ambiente protegido; shell/SSH ad hoc MUST NOT ser usado. A operação não aceita caminho arbitrário nem altera API/web, banco, Compose, Drive, configuração de backup, serviços ou timer.
- Propor uma operação protegida distinta para preparar e restaurar, como um conjunto, a ponte Compose, o forced command de preflight e `refs/remotes/origin/main`. O contrato exige inventário/fingerprint próprio somente de leitura, recibo root-only e cópias verificadas antes da primeira troca, uma única compensação verificável para falhas parciais e uma restauração pós-sucesso por digest do recibo. Essa operação não atualiza o checkout ativo nem altera aplicações, containers, configuração, serviços ou timer. O inventário completo do runtime e sua própria fingerprint continuam obrigatórios depois da preparação.
- Limitar a implantação ao Pick-your-Pic, com aprovação própria por etapa. O plano não inclui ativar expurgo, recuperar um tenant isoladamente ou substituir o processo de arquivo de fotos.
- Manter o baseline do classificador API/web igual ao SHA da última publicação confirmada, evitando que mudanças operacionais posteriores provoquem uma republicação sem alteração de runtime.

## Capabilities

### New Capabilities

- `media-storage/platform-backup-runtime`: execução interna de backup global no servidor, custódia e vinculação do destino, disparo manual, verificação de cópia e recuperação em ambiente isolado.

### Modified Capabilities

- `deployment-operations`: inventário, preparação e restauração protegidos do suporte usado pelo preflight de produção.

## Impact

Seletor autenticado da pasta, chamador de backup, configuração protegida, instalação e operação protegidas do runtime, agendamento exclusivo da Markina, workflow do wrapper com restauração pós-instalação por recibo, preparação/restauração do suporte de preflight e procedimentos de teste, recuperação e rollback. A restauração `restore-wrapper` continua limitada ao forced command do backup; a nova proposta cobre separadamente ponte, forced command de preflight e referência Git. Ambas usam cópias fixas root-only, recibos verificáveis e gates próprios. O Google Picker requer uma chave de navegador e o número do projeto Google Cloud; restringir a chave à origem oficial do app e às APIs necessárias. Não requer rota pública, migration, alteração de DNS ou ampliação do escopo OAuth.

## Estado e limites da aprovação

O proprietário aprovou a revisão da proposta restore-wrapper em 22/11/2026, somente para implementação e testes locais de 3.2u e CI na mesma PR. A aprovação não autoriza push antes da revisão do coordenador, merge, dispatch, acesso ao host/SSH, instalação/restauração no servidor, Drive, backup real ou timer. A conclusão de 3.2u ainda exige revisão humana do diff, merge autorizado e CI verde da main no SHA exato.

A proposta de preparação/restauração protegidas de `app-compose-bridge`, forced command de preflight e `refs/remotes/origin/main` foi registrada nesta atualização em 23/11/2026 para revisão. Ainda não foi aprovada para implementação. A autorização operacional anterior não substitui a revisão deste contrato, CI, inventário/fingerprint atual nem aprovação do ambiente protegido.
