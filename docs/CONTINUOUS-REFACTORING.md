# Política de refatoração contínua

## Alcance e prioridade

Toda implementação de funcionalidade, correção ou evolução SHALL considerar manutenção incremental do código diretamente afetado. Esta política vale também fora de comandos OpenSpec. O mandato, roadmap, contratos OpenSpec, isolamento entre clientes (tenants), segurança e autorizações existentes continuam obrigatórios.

A avaliação deve ser proporcional ao trabalho e acompanhar a entrega. Não exige auditoria geral, quota de remoções ou refatoração quando não houver oportunidade segura e relevante. A ausência de código elegível é um resultado válido.

## Avaliação e evidência

- Identifique, no escopo diretamente relacionado, código obsoleto, imports sem uso, CSS órfão, duplicações e componentes substituídos.
- Antes de remover ou reorganizar, comprove consumidores, compatibilidade e efeito da alteração. Para excluir, verifique ausência de consumidores estáticos e dinâmicos, integrações, testes, scripts, histórico relevante e contratos OpenSpec. Considere, conforme o componente, importação dinâmica, rotas, registros por convenção e classes CSS geradas em runtime.
- Uma busca textual sem ocorrências não basta como prova de desuso. Código antigo, pouco utilizado ou aparentemente redundante não é motivo suficiente para apagá-lo. Havendo dúvida sobre consumidor/contrato, preserve-o e registre a incerteza.
- A refatoração SHALL preservar compatibilidade retroativa e separação entre tenants. Regras financeiras, autenticação, banco/migrations, fotografias e dados de clientes só podem mudar por necessidade comprovada no trabalho autorizado e com a autorização apropriada; esta política não concede essa autorização.

## Execução incremental

Aplique somente remoções ou reorganizações diretamente relacionadas, suficientemente comprovadas e cobertas pela validação pertinente. Não misture a implementação com limpeza geral do repositório nem amplie a autorização de operações, dados ou ambientes.

Se a oportunidade ampliar significativamente risco ou escopo, registre-a como tarefa separada, com evidência, dependências e autorização necessária, e prossiga com a funcionalidade prioritária quando ela for independente e segura. Não execute a tarefa separada automaticamente fora do escopo aprovado. Se houver dependência real ou conflito de contrato, siga os gates de bloqueio já existentes.

## Integração ao desenvolvimento

1. **Proposta:** considere o impacto sobre o código existente e possíveis substituições ou duplicações na área afetada. Não invente oportunidades de limpeza.
2. **Tarefas:** inclua uma verificação proporcional do código substituído/obsoleto e do resultado esperado, com evidência verificável; ela pode integrar a própria task funcional. Registre separadamente manutenção que exceda o escopo.
3. **Implementação:** aplique apenas a manutenção elegível segundo os critérios acima. Registre brevemente o que foi removido/reorganizado e por quê, ou por que nenhuma ação era elegível. Alterações exclusivamente documentais podem registrar que não há código funcional afetado, sem iniciar busca geral.
4. **Fechamento:** revise o diff da área afetada para confirmar que não introduziu código morto evidente, duplicações desnecessárias ou regressões. Execute testes, lint, typecheck, build e validações OpenSpec pertinentes ao risco/escopo; resultados anteriores só são reutilizáveis enquanto suas premissas permanecerem válidas. Registre o resultado e limitações, sem declarar validação não executada.

## Fonte e aplicação das instruções

Este documento é a fonte única desta política. O `AGENTS.md` da raiz exige sua aplicação também em tarefas diretas. `openspec/config.yaml` a referencia no contexto, nas regras de proposal/tasks e na orientação de apply, preservando as instruções existentes.

O OpenSpec inclui essas orientações nos prompts; o executor deve aplicá-las e registrar evidências. Não se trata de uma ferramenta que detecta ou apaga código automaticamente, nem de um gate que prove ausência absoluta de código morto. Esta política não autoriza refatoração imediata, exclusão de arquivos antigos, deploy, acesso à Oracle, migrations, limpeza Docker ou alterações de dados.
