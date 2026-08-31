# Retenção do histórico comercial

Pedidos e itens permanecem como registros contábeis e auditáveis mesmo quando a
Galeria pública, a galeria privada e as fotos operacionais forem removidas. Apenas
itens confirmados recebem uma prévia protegida mínima e uma entrega final, ou uma
referência segura à entrega. Fotos não compradas e originais já cobertos por uma
referência externa não são copiados para formar histórico.

## Configuração da mídia

`COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS` define por quantos dias, contados da
confirmação do pedido, a prévia e a entrega histórica permanecem disponíveis.
O valor precisa ser um inteiro positivo. Quando a variável estiver ausente ou
vazia, nenhuma limpeza automática será feita. Este padrão deliberadamente não
presume prazo legal: homologação e produção só devem configurar o valor depois de
uma decisão documentada do controlador dos dados.

A rotina `apply_commercial_media_retention` remove apenas arquivos do namespace
isolado `MEDIA_HISTORY_ROOT`, limpa referências de entrega e marca o manifesto
como `purged`. Pedido, itens, valores, nomes das galerias e auditoria não são
apagados. A rotina é idempotente e não alcança originais nem derivados do acervo
operacional.

## Minimização de PII

`minimize_client_commercial_pii` exige que o chamador declare uma autorização de
privacidade válida. Ela limpa nome e telefone congelados nos pedidos daquela
cliente, registra o instante e uma auditoria somente com UUID e contagem. A
operação preserva a associação interna necessária, valores, itens, termos
comerciais, nomes das galerias e datas. Sem autorização expressa, a operação é
recusada e nenhum dado é alterado.
