# Proposal

## Why

O Pick-your-Pic ainda precisa de um contrato implementável para cópia cifrada e recuperação do PostgreSQL global depois que a tentativa antiga baseada em Google Workspace foi aposentada. A prova sintética com Restic e Rclone demonstrou interoperabilidade local e restauração verificável, mas não cobre integração SaaS, destino externo, custódia de chave nem recuperação operacional.

## What Changes

- Definir uma capacidade de backup e recuperação do PostgreSQL global com Restic como formato/engine de snapshots e Rclone como transporte, sem criar outra engine de backup.
- Estender a operação do proprietário em `/admin/platform` para configurar e acompanhar o estado persistido, solicitar cópia e preparar/acompanhar recuperação. A UI SaaS será a interface operacional normal; Backrest poderá ser avaliado apenas como ferramenta interna opcional, sem UI/API pública ou dependência de uma segunda interface.
- Cobrir a base PostgreSQL global de forma coerente e cifrada, com verificação de integridade e ensaio de restauração isolada. O backup inclui os dados presentes no banco, inclusive dados de todos os fotógrafos e registros sensíveis que estejam persistidos nele; não inclui bytes de fotos, arquivos `.env`, chaves de sistema ou volumes de mídia.
- Manter backup PostgreSQL, arquivo frio de mídia e objetos do Google Drive em raízes, identidades, chaves e políticas separadas. Pela decisão do proprietário, objetos Drive já existentes continuam no Drive sem migração automática; novos objetos Rclone de arquivo frio terão identidade explícita de provider. A proposta não altera a change #441 nem implementa o provider de mídia.
- Preservar operações protegidas, auditoria, estados sanitizados `unknown`/`unavailable`/`stale` e validação por restauração antes de qualquer promoção. Uma leitura comum da página não consulta o destino remoto.
- Após restauração, impedir que workers reproduzam automaticamente efeitos externos até que filas e operações duráveis sejam reconciliadas; isso reutiliza os workers existentes e não cria uma nova fila.
- Manter a retenção automática desativada até a política ser confirmada para esta implementação. A proposta registra como decisão pendente a reconciliação entre a política histórica de 7 diários/4 semanais/3 mensais e a orientação posterior de manter somente a cópia diária mais recente depois de validada.
- Delimitar decisões ainda necessárias sobre destino externo, custódia e recuperação da chave, metas RPO/RTO, procedimento de recuperação se a aplicação estiver indisponível e autorização de eventual substituição do banco de produção.

## Capabilities

### New Capabilities

- `deployment-operations/global-postgresql-backup`: ciclo de backup cifrado e recuperação verificável da base PostgreSQL global usando Restic/Rclone, separado do armazenamento de mídia.

### Modified Capabilities

- `platform-admin/owner-console`: operação e recuperação do backup global pela interface autenticada existente do proprietário, com reautenticação, auditoria e estados de disponibilidade seguros.

## Impact

Esta change é somente documental. A implementação futura poderá envolver backend, worker/agendamento, configuração privada do servidor, integração com a UI administrativa e testes sintéticos; não pressupõe migration, destino ou credencial já escolhidos. Não reativa `platform_backup`, Google Picker ou a integração aposentada de Google Workspace. Não altera o domínio de jobs, catálogo, cobrança, fila ou mídia, nem cria uma fila nova; a recuperação apenas exige suspender workers existentes até reconciliar operações. O ensaio local concluído é evidência limitada a PostgreSQL sintético e Restic/Rclone sobre destino local; integração de produção, destino remoto, custódia independente da chave e recuperação operacional ainda exigem desenho e validação próprios.
