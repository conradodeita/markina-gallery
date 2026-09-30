# Validação do planejamento

## Estado

Planejamento local em 30/09/2026, branch `feature/plan-small-multi-photographer-pilot`, base `ce628f01d4aa9f7f9d7eb24bf347e30ae42579d3`. Nenhuma tarefa de implementação concluída; banco, credenciais, canais e ambientes permanecem fora desta execução de planejamento.

## Decisão e fontes

- O proprietário confirmou cadastro independente por fotógrafo, incluindo o caso de dois fotógrafos atendendo a pessoa com o mesmo telefone. Registrado em proposal, design e specs de isolamento/autenticação/diretório.
- Leitura de mandato, roadmap, configuração OpenSpec, specs relevantes, artefatos da fundação e código de tenancy/identidade mostrou que ownership de galerias/fotos já existe, mas clientes/configurações e gates ainda pressupõem conta única.
- `gh pr view 115 --json state,mergedAt,mergeCommit,url`: PR integrado em `ff680e411d0c04fd3ca82c1885204891f56451a9`, 29/09/2026 às 20:41:11 UTC. Seus artefatos ainda dizem rascunho e têm 6.2–6.5 pendentes. Integração não comprova todos os aceites dessas tarefas; a reconciliação ficou como task 1.1 e não foi marcada por inferência.
- PR #128 e run [36745688654](https://github.com/conradodeita/markina-gallery/actions/runs/36745688654) confirmados como integrado/concluído com sucesso para `32fc8f5ad07184bbe6e2ea61fc504e29ab70cfd5`. As evidências funcionais anteriores do monitor foram acrescentadas ao `validation.md` da change arquivada correspondente.

## Validação

- `npx -y @fission-ai/openspec@latest status --change add-small-multi-photographer-pilot`: 4/4 artefatos de planejamento completos (proposal, specs, design, tasks).
- `npx -y @fission-ai/openspec@latest validate add-small-multi-photographer-pilot --type change --strict --no-interactive`: válida após preservar os títulos dos cenários existentes e corrigir a sintaxe FROM/TO do requisito renomeado.
- Sete capacidades correspondem aos sete deltas. Os blocos MODIFIED do diretório, PIX e avisos conservaram integralmente cenários e proteções existentes, acrescentando a fronteira de conta. Autenticação e monitor mantêm os cenários anteriores e acrescentam negativas de contexto/permissão.
- Revisão de coerência: identidade independente não permite fallback global; OTP e sessão vinculados ao mesmo fotógrafo; PIX/carrinho restritos à conta; jobs/caches/mídia/retention incluídos na matriz; monitor agregado exige permissão separada; piloto não se apresenta como benchmark ou autorização biométrica.
- Mudanças restritas aos artefatos desta proposta e ao complemento documental da validação anterior. Nenhum arquivo de aplicação, migration, ambiente ou segredo alterado. Testes de aplicação não foram repetidos porque esta entrega não altera código.

## Próxima ação

Revisão do proprietário sobre a proposta completa, incluindo tamanho 2 × 3, permissão técnica do dono e provisionamento/canais controlados. Após aceite explícito da implementação, iniciar task 1.1. Aprovação da decisão sobre clientes, isoladamente, não constitui aceite de todas as decisões arquiteturais nem autorização de deploy.
