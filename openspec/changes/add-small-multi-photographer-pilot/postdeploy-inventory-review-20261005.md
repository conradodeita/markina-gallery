# Revisão do inventário de manutenção pós-deploy — 05/10/2026

## Aceite

O proprietário aceitou a alteração após o diagnóstico do run #375: o deploy-homolog concluiu para o merge `53a595f`, e a etapa posterior falhou porque o modo `inventory` exigia exatamente um fotógrafo numa instalação com três. O aceite cobre a correção local e a publicação desta correção pelo fluxo de PR, com commit e CI autorizados nesta conversa. Não autoriza executar cleanup nem dispensa o inventário e o plano de impacto zero antes da publicação em homologação.

## Alteração

Somente `inventory` aceita instalação multitenant. O relatório mantém contagens agregadas por tabela/categoria e tipo de mídia, inclui a quantidade total de fotógrafos e indica `unavailable_multiple_photographers` para a limpeza destrutiva. Não retorna identificadores nem linhas por fotógrafo. `execute` mantém a exigência de proprietário único, confirmação literal, homologação, PostgreSQL, schema conhecido e volumes exclusivos.

## Validação local

- `backend/tests/test_homolog_cleanup.py`: 10 passed, 1 skip (teste de limpeza destrutiva exige PostgreSQL).
- `scripts/test_maintain_homolog_policy.py`: aprovado; cobre modo default inventory e guarda do execute.
- Ruff nos arquivos afetados: aprovado.
- OpenSpec estrito: `add-small-multi-photographer-pilot` válido.
- Integrações PostgreSQL sintéticas de inventário/execução: não executadas, pois `PHOTOGRAPHER_TEST_DATABASE_URL` não está configurada. A guarda de `execute` também tem teste local isolado com conexão mockada e duas contas, que recusa antes de ler mídia.

Este registro não afirma que o run #375 foi repetido ou que um novo deploy já ficou verde.
