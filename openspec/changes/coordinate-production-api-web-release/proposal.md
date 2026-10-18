# Proposal

## Why

O repositório já possui um fluxo de produção aprovado via GitHub Actions para publicar `api` e `web`, além de um fluxo operacional web-only. Como os dois podem executar fora do mesmo controlador, precisam compartilhar uma exclusão mútua no host para impedir que alterem serviços ou estado de release ao mesmo tempo.

## What Changes

- Fazer releases e rollbacks mutáveis de API+web adquirirem o mesmo lock de host já usado pelo fluxo web-only.
- Recusar operação API+web quando o lock estiver ocupado, `flock` estiver indisponível, o estado do lock não existir ou houver tentativa web-only sem conclusão.
- Preservar os gates, a aprovação protegida, os snapshots e o rollback do fluxo GitHub Actions existente.
- Preservar o fluxo web-only e sua recusa quando houver operação API+web em andamento ou pendente.
- Documentar a exclusão mútua nos runbooks e testar ambos os sentidos da concorrência.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: requer serialização entre releases mutáveis API+web e web-only usando um lock de host comum.

## Impact

A alteração limita-se ao script de release API+web já existente, ao helper e testes do fluxo web-only, aos runbooks e à change OpenSpec. Não cria um segundo mecanismo de release, não altera os gates existentes de produção e não modifica serviços, dados, schema, workers ou infraestrutura.