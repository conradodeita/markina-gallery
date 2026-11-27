# Backup global e recuperação de pastas frias

> Documento atualizado em 25/11/2026. A tentativa própria de backup global via Google Workspace foi encerrada. Os registros e recibos antigos são apenas evidência histórica; não reutilizar nem reinstalar seus módulos, credenciais, chaves ou workflows.

## Direção vigente

A change [prove-open-source-backup-and-recovery](../../openspec/changes/prove-open-source-backup-and-recovery/proposal.md) exige uma prova local/sintética conjunta para:

- backup global cifrado do PostgreSQL e restauração isolada;
- extração seletiva de um fotógrafo a partir de uma cópia global restaurada;
- arquivo e recuperação de pasta fria pelo fluxo existente do fotógrafo.

Restic e Rclone são candidatos comuns; Backrest é opcional para acompanhamento. A change ainda não prova implantação, configuração real de produção ou acesso ao Drive. Não fazer deploy, usar credenciais reais, criar outra fila nem iniciar uma rotina produtiva como parte da prova.

## Contrato existente da pasta fria

O fluxo de recuperação por fotógrafo permanece no produto e não foi retirado junto com o backup global. Ele usa os contratos e dados do domínio media archive:

- elegibilidade depois do prazo configurado da pasta mais 30 dias;
- solicitação por 7, 14 ou 30 dias e cobrança configurável por pasta/ciclo;
- reserva idempotente de créditos e débito somente após recuperação integral conferida por tamanho e SHA-256;
- falha comprovada libera a reserva; resultado incerto exige reconciliação e preserva a reserva;
- proprietário isento; sem expurgo automático.

O futuro motor pode compartilhar ferramentas, mas as identidades, raízes, chaves, namespaces, retenção e autorização permanecem separados. Não misturar restore global, extração de fotógrafo e recuperação de objeto frio.

## Implementação que deve ser preservada

A UI, API, fila, catálogo, manifesto, staging e ledger atuais da pasta fria são consumidores ativos. Os módulos backend media_archive, a composição do adaptador Drive e suas migrations não são parte da tentativa global aposentada e não devem ser removidos nessa limpeza.

As provas antigas de upload/readback no Drive e restore PostgreSQL sintético comprovam somente aqueles ensaios históricos. Elas não provam runtime ativo, cópia recorrente, credencial instalada ou recuperação operacional atual.

## Próxima tarefa

Começar pela task 1.1 da change prove-open-source-backup-and-recovery e registrar resultados e limites em tasks.md. Não reabrir as changes enable-platform-backup-runtime, prepare-platform-backup-source ou add-google-workspace-backup-copy.
