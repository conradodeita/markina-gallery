# Validação da política permanente

## Compatibilidade efetivamente verificada

- CLI instalado: OpenSpec 1.14.1. Schema ProjectConfigSchema aceitou a configuração; carregamento preservou schema/context e as três orientações apply anteriores.
- CLI do CI: OpenSpec 1.14.0, sem alterar o pin ou qualquer workflow.
- Nas duas versões, `instructions proposal --change establish-continuous-refactoring-policy --json` inclui a referência no context e uma regra proposal; `instructions tasks` inclui duas regras; `instructions apply` inclui cinco orientações, sendo três preexistentes e duas novas.
- A change passou em `validate establish-continuous-refactoring-policy --strict` nas duas versões.
- `npx --yes @fission-ai/openspec@1.14.0 validate --strict --all --json`: 123 itens aprovados, zero falhas (101 changes e 22 specs). Mantida a validação integral do CI.

## Escopo, preservação e manutenção proporcional

A raiz AGENTS recebeu apenas uma referência obrigatória. A configuração recebeu somente acréscimos nos campos suportados; as regras anteriores foram preservadas. Links locais, UTF-8 e diff foram conferidos. Nenhum arquivo antigo foi excluído ou renomeado.

Esta implementação afeta apenas instruções/documentação: não há código funcional substituído ou obsoleto elegível para remover. A ausência de limpeza foi aceita sem auditoria geral ou remoção artificial. Não foram criados testes de produto para uma mudança sem código funcional; os testes de CI existentes continuam obrigatórios para integração.

A declaração skip_specs segue o contrato de tooling do CLI: nenhum requisito de produto foi alterado. Nenhuma spec funcional, migration, dependência, script, workflow, configuração de ambiente, dado de cliente ou recurso Oracle foi modificado.

## Gates de integração

Workflows versionados preservados. CI isolado em pull_request; push da branch de trabalho não é gatilho. Push main classifica o delta desde o baseline registrado; produção depende de escopo app/facial, homolog de push develop e rollback de despacho manual. Outros três workflows são manuais, sem closed/workflow_run/workflow_call/pull_request_target. Nenhum hook/ruleset adicional retornado; o cadastro legado remote-test-smoke não tem arquivo nesta linha.

Main exige os seis checks estritos e aplica as proteções a administradores; nenhuma aprovação formal obrigatória no estado consultado. Integração somente com todos os resultados definitivos, base/head conferidos e sem bypass/force push. CI do PR, decisão de merge e CI pós-merge serão verificáveis no GitHub; este registro local não antecipa seus resultados.

## Revisão documental

Code Review local em modo read-only identificou que a política nova ainda estava untracked e, portanto, ausente do diff Git. O arquivo será incluído explicitamente no commit junto com suas referências; não se trata de arquivo ausente no workspace. A revisão final incidirá sobre o diff completo já versionado.

A política e todos os artefatos foram incluídos no commit 80fd4e7. A revisão final local read-only sobre o diff completo terminou com código 0, sem defeitos acionáveis. Classificador desse commit: release_scope=none, baseline fe1f3bc6e1a483bd1ac5f4e71149f903e724873f. A main permaneceu f839d87e066f004954492bd552ad016f6fbddd9b durante a preparação; a classificação e os gates serão repetidos no head final antes da integração.
