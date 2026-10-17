# Tasks

## 1. Contrato e agregação comercial

- [x] 1.1 Criar serviço/DTO de estatísticas baseado em tenant resolvido no servidor e filtros comuns de período, evento, galeria, pasta, cliente e pagamento; verificar que cada lista de opções e consulta usa o mesmo tenant.
- [x] 1.2 Calcular receita e pedidos somente para confirmações financeiras vigentes; derivar método dos vínculos PIX/InfinitePay, excluir estados pendentes/cancelados/corrigidos/hold e cobrir pedidos agrupados sem contagem duplicada.
- [x] 1.3 Consolidar pedidos, itens, fotos, clientes, galerias e pastas por snapshots persistidos; calcular quantidade de itens e ticket médio com denominadores documentados.
- [x] 1.4 Conciliar soma dos preços unitários com total do pedido, retornar divergências explícitas e comprovar soma por pasta/galeria e total por escopo.

## 2. Dashboard administrativo

- [x] 2.1 Evoluir `/admin/statistics` com KPIs confiáveis, hierarquia visual responsiva, estados carregando/vazio/erro e distinção entre receita efetiva e seleções sem compra.
- [x] 2.2 Implementar filtros combináveis por período, evento, galeria, pasta, cliente, forma de pagamento e status; garantir drill-down e paginação das linhas detalhadas.
- [x] 2.3 Preservar recursos atuais de paginação, retry e TXT legado até revisão de compatibilidade, com testes de regressão.

## 3. Relatórios

- [x] 3.1 Gerar HTML responsivo e autocontido a partir do serviço e filtros compartilhados, sem dependência de sessão, rede, credenciais ou URLs privadas.
- [x] 3.2 Gerar CSV por item com cabeçalhos e formato documentados, escaping correto, UTF-8, centavos exatos e total do pedido fora das linhas de itens.
- [x] 3.3 Proteger o endpoint CSV com sessão e tenant ativos mais o UUID de proprietário persistido; verificar negação antes da consulta, revalidação depois da consulta e ausência de mudança no Monitor.
- [x] 3.4 Garantir que HTML e dashboard usem os mesmos filtros, estados financeiros, itens e divergências de conciliação; no CSV, comparar soma das linhas de item ao mesmo escopo sem repetir total do pedido.

## 4. Abandono e conversão

- [x] 4.1 Definir a regra de abandono com o proprietário. Decisão recebida em 2026-10-16: usar expiração do prazo configurado da galeria/cliente, sem prazo global adicional.
- [x] 4.2 Classificar de forma idempotente seleções persistidas expiradas sem qualquer pedido associado; manter pedidos pendentes, cancelados, confirmados e finalizados sem cobrança em estados próprios. Não requer evento ou coluna nova porque o vencimento está persistido.
- [x] 4.3 Calcular quantidade e fotos abandonadas uma vez por cliente/galeria e valor potencial somente quando existir snapshot comercial confiável; valor desconhecido SHALL ser nulo, sem recalcular preços atuais.

## 5. Validação e documentação

- [x] 5.1 Cobrir pagamentos PIX/cartão, pedidos múltiplos, itens em pastas diferentes, cliente com pedidos múltiplos, pendentes, cancelados, corrigidos/hold, snapshots após exclusão, divergência financeira e filtros combinados.
- [x] 5.2 Cobrir CSV por item, encoding/escaping, reconciliação, HTML offline e igualdade de escopo entre dashboard/HTML/CSV.
- [x] 5.3 Cobrir autorização direta do CSV para proprietário, fotógrafo não proprietário, sessão/vínculo inválido, registro ausente e tentativa de usar outro tenant.
- [x] 5.4 Executar validações direcionadas, suítes aplicáveis, Ruff, lint, typecheck, build, validação OpenSpec e revisão do diff sem tocar Monitor, segredos ou deploy.
- [x] 5.5 Registrar limitações de reembolso, ajustes e abandono que permaneçam fora dos dados persistidos; não marcar tasks bloqueadas como concluídas.
