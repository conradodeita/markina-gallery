## Context

Veja `proposal.md`. A implementação atual já persiste seleções, favoritos, comentários e pedidos por cliente, mas a autorização de galeria ainda exige que o cliente seja o único titular armazenado na galeria derivada. Há uma tabela de acesso iniciada, porém ela não é a fonte única de autorização nem representa o ciclo individual completo.

## Goals / Non-Goals

**Goals:**

- Tornar o vínculo de acesso a fonte de verdade para autorização de responsáveis em uma galeria compartilhada.
- Preservar isolamento de dados pessoais e comerciais por responsável.
- Dar ao fotógrafo uma lista e ficha operacionais sem dados simulados ou consulta de dados sensíveis no browser.
- Preparar o ponto de integração pelo qual um resultado facial aprovado poderá criar uma galeria derivada e seus vínculos, sem habilitar biometria.

**Non-Goals:**

- Criar pastas, upload em lote, sugestões editoriais, cobertura de galeria, preço por faixa, checkout, mensagens automáticas, identidade visual, gateway ou entrega.
- Expor o acervo-mãe, liberar galeria coletiva pública ou executar busca facial.

## Decisions

### Proprietária persistente e vínculos como autoridade de acesso

Cada galeria derivada preservará uma cliente proprietária, que identifica a origem e titularidade da galeria privada. Cada combinação galeria-responsável terá também um vínculo único com estado individual e auditoria. A autorização de leitura e escrita consultará o vínculo ativo, enquanto a titularidade continuará armazenada separadamente. Seleções, favoritos, comentários e pedidos já possuem identidade de cliente e permanecerão assim.

O campo de cliente titular legado será preservado e seu valor será migrado para um vínculo ativo inicial. Usá-lo sozinho para autorização foi descartado porque impediria responsáveis adicionais; removê-lo foi descartado porque apagaria a titularidade de negócio e dificultaria rollback seguro.

### Estados de galeria e estados por responsável separados

O prazo de seleção e a configuração geral pertencem à galeria compartilhada. Bloqueio/liberação pertencem ao vínculo individual. A aba “congeladas” conterá galerias cujo prazo já venceu; galerias com acesso individual bloqueado continuam na lista ativa e podem ser filtradas por bloqueio. Pedidos e entregas não são removidos por expiração.

O resumo operacional por responsável será calculado no backend a partir de seleções e pedidos existentes. Esta mudança não inventará novos estados financeiros; a futura mudança de checkout/pagamento poderá enriquecer o mesmo contrato.

### Link como contexto, não como credencial

O link compartilhável identifica a galeria e preserva seu contexto na entrada, mas não contém segredo nem autoriza fotos. Após OTP, o backend confirma o vínculo ativo do telefone autenticado antes de encaminhar à galeria; tentativas sem vínculo recebem resposta neutra.

Links individuais opacos foram descartados nesta etapa porque o produto já define vínculo persistente e OTP como mecanismo de acesso. Convites revogáveis poderão ser acrescentados posteriormente sem alterar o vínculo.

### Consultas administrativas mínimas e orientadas pelo backend

A lista usará filtros e paginação fornecidos pela API administrativa. Busca por telefone será normalizada no servidor e restrita ao fotógrafo autenticado; as respostas listarão somente os dados necessários para identificação operacional. A capa administrativa usará apenas uma prévia já autorizada, sem URL de original.

### Integração futura com descoberta facial aprovada

Após o spike biométrico aprovado, a revisão humana poderá criar ou reutilizar uma galeria derivada, atribuir somente as fotos aprovadas e criar um vínculo individual de acesso para o responsável. Essa integração usa exatamente os mesmos contratos de galeria, vínculos e isolamento desta mudança; ela não cria acesso ao acervo-mãe nem resultados públicos.

## Risks / Trade-offs

- [Migração de galeria existente falhar ou duplicar vínculo] → migração idempotente, constraint de unicidade, teste de upgrade/downgrade e preservação do titular atual como único vínculo inicial.
- [Bloqueio individual confundir-se com expiração] → contratos e rótulos distintos para acesso bloqueado e galeria congelada.
- [Busca administrativa expor mais telefone que o necessário] → autorização administrativa, resposta mínima, logs de auditoria e testes de ausência de dados em rotas de cliente.
- [Responsável compartilhar link] → OTP e vínculo ativo continuam obrigatórios; link sozinho não revela a galeria.
- [Spike facial ser reprovado] → o fluxo manual de criação/vínculo continua funcional e nenhuma interface biométrica depende desta mudança.

## Migration Plan

1. Criar migration aditiva para normalizar e restringir os vínculos galeria-responsável, migrando cada cliente titular existente para um único vínculo ativo.
2. Atualizar autorização e contratos com testes de isolamento entre dois responsáveis da mesma galeria.
3. Publicar lista e ficha administrativas após contratos estáveis, com dados sintéticos em homologação.
4. Validar migration, testes, lint, build e OpenSpec antes de publicação. Rollback restaura os serviços anteriores; a migration preserva o campo legado até a validação pós-publicação e não remove histórico comercial.
