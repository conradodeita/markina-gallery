## Why

Galerias criadas depois da ativação permanente do subsistema facial ficam com “Rollout não disponível” porque a ausência de um registro individual ainda é interpretada como bloqueio. Isso contradiz a operação atual, na qual o fotógrafo não deve preparar nem ativar reconhecimento manualmente em cada nova galeria.

## What Changes

- Tratar `FACIAL_PROCESSING_ENABLED=true`, ambiente coerente e calibração válida como disponibilidade facial padrão para galerias ativas sem rollout individual.
- Expor essas galerias ao painel como `active/general`, eliminando os estados enganosos “Reconhecimento falhou” e “Rollout não disponível” causados somente pela ausência do registro.
- Preservar registros explícitos `prepared`, `suspended` ou `revoked` como bloqueios por galeria e manter a possibilidade de interrupção imediata pelo kill switch global.
- Fazer a regra valer tanto para galerias futuras quanto para galerias ativas já existentes sem rollout, sem migration, backfill ou reprocessamento automático de mídia.
- Manter admissão, execução, consentimento da cliente, retenção, isolamento e demais gates técnicos existentes.

## Capabilities

### New Capabilities

- `privacy-biometric/automatic-facial-availability`: definir a disponibilidade facial geral de galerias ativas a partir do estado efetivo do ambiente e dos bloqueios explícitos.

### Modified Capabilities

Nenhuma.

## Impact

- Backend facial: resolução de disponibilidade, payload administrativo e testes de rollout/status/indexação.
- Frontend: nenhuma nova interface; o painel existente passará a receber `active/general` para galerias abrangidas pelo padrão.
- Banco e mídia: nenhuma migration, escrita em massa, duplicação de arquivo ou reprocessamento automático.
- Operação: o kill switch e os workers existentes permanecem inalterados; produção continua dependente da calibração aprovada antes de qualquer disponibilidade geral.
