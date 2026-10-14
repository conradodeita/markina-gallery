## 1. Vínculos e autorização compartilhada

- [ ] 1.1 Criar migration aditiva que torna único o vínculo galeria-responsável, preserva o cliente proprietário atual como titular e vínculo ativo inicial e verifica upgrade/downgrade em banco sintético.
- [ ] 1.2 Centralizar a autorização da cliente no vínculo ativo e atualizar biblioteca, galeria, seleções, favoritos, comentários, pedidos e prévias; verificar testes de isolamento entre dois responsáveis da mesma galeria.
- [ ] 1.3 Implementar criação, bloqueio, liberação e consulta auditável de vínculos individuais; verificar que bloquear um responsável não interrompe o acesso dos demais.
- [ ] 1.4 Preservar contexto de link controlado até o OTP e retornar resposta neutra a pessoa sem vínculo; verificar que o link não concede acesso nem revela a galeria.

## 2. Contratos operacionais do fotógrafo

- [ ] 2.1 Implementar API administrativa paginada de galerias com busca normalizada por nome/telefone, abas ativa/congelada e filtros backend-driven; verificar autorização e ausência de dados sensíveis em rotas de cliente.
- [ ] 2.2 Implementar contrato de ficha da galeria com capa autorizada, responsáveis, resumo individual de seleção/pedido, estado de acesso e prazo; verificar contrato com testes de API.
- [ ] 2.3 Implementar ações administrativas de adicionar/cadastrar responsável, bloquear/liberar vínculo e reativar prazo; verificar auditoria, idempotência e preservação de pedidos anteriores.

## 3. Superfícies administrativas

- [ ] 3.1 Criar lista de galerias backend-driven com busca, filtros, ordenação operacional, estados vazio/erro/carregando e navegação por foto ou título; verificar lint e renderização autorizada.
- [ ] 3.2 Criar ficha de galeria com link controlado, responsáveis vinculados, ações individuais e reativação de prazo; verificar que ações destrutivas pedem confirmação explícita.
- [ ] 3.3 Atualizar biblioteca e galeria da cliente para a autorização compartilhada, sem expor dados ou interações de outro responsável; verificar fluxo em testes de componente e integração.

## 4. Qualidade, homologação e continuidade

- [ ] 4.1 Cobrir migration, autorização, vínculo múltiplo, bloqueio individual, expiração, reativação, busca administrativa e link controlado com testes automatizados; verificar `pytest backend/tests -q`.
- [ ] 4.2 Validar frontend com `npm run lint` e `npm run build`, incluindo estados visuais e acessibilidade das novas rotas.
- [ ] 4.3 Validar OpenSpec em modo estrito e homologar com dados exclusivamente sintéticos, registrando versão, resultado, rollback e que o reconhecimento facial não foi ativado.
