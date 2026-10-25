# Tasks

## 1. Serviço de recuperação e transação

- [x] 1.1 Implementar prévia/reabertura por compra com ownership, confirmação explícita, fingerprint, seleção integral, histórico e idempotência; executar regressões sintéticas de PIX/cartão disponíveis, fotos novas, simulação/rollback, estado confirmado/falha clara, snapshot e repetição após nova compra. Registrar evidências e revisão proporcional de reutilização.
- [x] 1.2 Proteger a emissão contra resposta tardia e testar reabertura/confirmador/emissão concorrentes em PostgreSQL isolado, comprovando ausência de regressão de estado e de restauração duplicada.

## 2. API e card da cliente

- [x] 2.1 Expor prévia/confirmação administrativas, capacidade/revisão/indicador na projeção e revisão de recuperação da própria cliente no carrinho; testar autenticação, isolamento A/B, inputs, conflito, fotos canônicas e preservação de decisões PIX/receitas/entregas.
- [x] 2.2 Implementar Reabrir carrinho no card da cliente por compra e retomada no carrinho com chave nova após reabertura validada, sem selecionar novamente; executar testes de componente para prévia/confirmar/cancelar, falha, duplo clique, estados confirmados sem ação e idempotência da emissão incerta, mantendo filtros/fotos/paginação.
- [x] 2.3 Identificar reabertura auditada no histórico da cliente com acesso ao carrinho e omitir rascunho PIX não comunicado do painel financeiro, preservando seleção, comunicação/confirmados e registros. Reproduzir o cenário e executar regressões API/UI.
- [x] 2.4 Aplicar a mesma visibilidade comercial às listas de pedidos da galeria e ao contador de pedidos no diretório do fotógrafo, sem alterar inventário/proteção de exclusão. Comprovar que o rascunho não reaparece como pedido duplicado nas demais telas e que pagamentos comunicados continuam visíveis.

## 3. Integração e entrega

- [x] 3.1 Executar gates locais pertinentes (backend focado/amplo, PostgreSQL, Ruff, frontend testes/lint/TypeScript/build, OpenSpec), revisar diff por regressões/duplicação e preparar PR draft empilhado sobre #263 com evidências, plano mínimo de publicação/rollback e bloqueios reais. Não modificar #261/#262/#264, publicar, mesclar ou alterar compras reais.
- [x] 3.2 Corrigir a conversão do UUID recebido por HTTP na consulta de teste apontada pelo CI 39660195152, reproduzir a falha e repetir os testes da API em SQLite, preservando todas as expectativas de produto. Executar Ruff/OpenSpec e revisar o diff antes de enviar a correção ao mesmo PR draft; o novo CI completo permanece gate externo.
- [x] 3.3 Preparar allowlist/manifesto com arquivos e blobs exatos de #263/#265 e baseline saudável observada, reproduzir o bloqueio e executar regressões de escopo/classificação/políticas e OpenSpec, sem ampliar serviços, dependências ou scripts operacionais. Revisar o diff e enviar ao mesmo PR; o novo CI completo é gate de 3.4.
- [x] 3.4 Revisar/integrar os PRs necessários pelo procedimento oficial e conferir o CI do SHA integrado, sem bypass; preparar o alvo e apresentar inventário, impacto e rollback vinculados ao candidato exato. Evidência: PRs #263/#265 integrados em 21b89c3; CI 39679561004 completo success, preflight oficial e aprovação protegida humana registrados em validation.md.
- [x] 3.5 Executar somente o release autorizado API/web; verificar identidade, schema, saúde/HTTPS, isolamento de rotas e preservação dos demais serviços e registrar recibos. Rollback apenas se necessário e pelo fluxo inventariado, sem operações financeiras reais ou restauração de banco. Evidência: release oficial saudável às 22:15:31 UTC de 21/10/2026, inventário posterior e verificações somente-leitura em validation.md; nenhum rollback necessário.

## Workflow follow-up

- Publicação de API/web exige autorização operacional própria; a autorização de implementar a ação manual não autoriza deploy ou novos pagamentos reais.
- CI completo do head final do PR #265 é gate externo obrigatório antes de declarar aptidão para publicação; acompanhar o resultado no próprio PR/run. O resultado parcial/antigo não vale como CI final, mesmo com tasks locais concluídas.
- Após o push da correção de 39660195152, o proprietário acompanhará o novo CI e trará o resultado; o executor deve parar o acompanhamento conforme instrução expressa de 21/10/2026.
- O proprietário posteriormente retomou o acompanhamento e autorizou o deploy após CI 39666630350 aprovado em 6f4a903. Tasks 3.3–3.5 são a etapa operacional; essa autorização não dispensa gates técnicos, fingerprint, proteção do ambiente ou rollback.
- A publicação foi concluída pelo workflow oficial após aprovação protegida de conradodeita; o proprietário habilitará cartão pela UI. Validação visual autenticada e pagamento real permanecem verificações do proprietário, não executadas pelo agente. Após este release, o seguimento solicitado é retomar separadamente #262; não antecipar migration/keyring/cofre na publicação de schema 0084.
- Sincronizar/arquivar somente após revisão humana. Gates de webhook/reconciliação universal continuam como seguimento independente.
