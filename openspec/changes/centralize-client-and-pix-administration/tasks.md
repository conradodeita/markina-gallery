## 1. Inventário e contratos de regressão

Escopo desta implementação: PIX global, conforme `pix-implementation.md`. Tarefas do diretório/lifecycle de clientes permanecem planejadas e não são consideradas entregues. Checkboxes mistos só serão fechados quando ambas as partes tiverem evidência.

- [ ] 1.1 Inventariar modelos, FKs, endpoints e consumidores atuais de cliente e PIX, confrontar dependências com as changes ativas e registrar qualquer conflito antes do código; verificar o inventário por busca reproduzível e revisão do diff.
- [ ] 1.2 Adicionar testes inicialmente falhos para listar e administrar clientes sem galerias, manter vinculadas na busca e excluir uma cliente com privada operacional sem compra; verificar também o bloqueio de histórico comercial e o isolamento de outra cliente.
- [ ] 1.3 Adicionar testes inicialmente falhos para PIX global, confirmação sensível, backfill idêntico/divergente, leitura na etapa 02 e snapshot imutável no checkout.

## 2. Persistência e migration aditiva

- [ ] 2.1 Modelar a configuração PIX global versionada e o recibo idempotente de exclusão de cliente, com constraints, timestamps UTC e ausência de PII no recibo; verificar criação em banco limpo e validações do modelo.
- [x] 2.2 Ampliar o propósito do desafio administrativo para alteração PIX e vincular de forma cifrada/fingerprinted a proposta e a sessão; verificar que chave, BR Code e OTP não aparecem em `repr`, logs ou auditoria.
- [x] 2.3 Criar migration Alembic aditiva no head vigente, mantendo `pix_checkout_settings` legado e snapshots; verificar upgrade/downgrade em banco limpo e existente.
- [x] 2.4 Implementar backfill canônico `zero → unconfigured`, `um valor → active`, `valores divergentes → review_required`; verificar que nenhuma divergência escolhe recebedor arbitrariamente e que pedidos permanecem byte a byte inalterados.

## 3. Diretório e lifecycle de clientes no backend

- [ ] 3.1 Expandir a listagem administrativa de clientes com paginação, busca e agregados em lote de públicas, privadas, pedidos e elegibilidade de exclusão; verificar ordem estável, ausência de N+1 e autorização administrativa.
- [ ] 3.2 Reclassificar o inventário entre dependências operacionais removíveis e histórico comercial protegido, incluindo o estado facial transitório; verificar cada categoria e a ausência de falsos bloqueios por vínculo sem compra.
- [ ] 3.3 Implementar a exclusão síncrona, transacional e idempotente do grafo operacional da cliente, preservando públicas, JPEGs, privadas compartilhadas e terceiros; verificar sucesso imediato, repetição, rollback e corrida com novo pedido.
- [ ] 3.4 Remover privada exclusiva sem histórico e preservar privada com outros membros, eliminando somente interações individuais; verificar referências administrativas, seleções, capabilities, sessões e arquivos físicos em testes de integração.
- [ ] 3.5 Preservar o bloqueio para qualquer histórico comercial e retornar inventário acionável sem PII; verificar pedidos pendentes/confirmados, pagamentos, entregas e snapshots.
- [ ] 3.6 Manter edição de nome e troca verificada de telefone na identidade canônica, invalidando acessos dependentes do número anterior e recusando duplicidade; verificar vínculos e histórico no mesmo UUID.
- [ ] 3.7 Registrar auditoria sanitizada e recibo da exclusão com ator, UUID, contagens e resultado; verificar ausência de nome, telefone, chave PIX, conteúdo comercial e duplicação por retry.

## 4. Diretório global de clientes no frontend

- [ ] 4.1 Extrair cadastro, edição, troca de telefone, inventário e confirmação de exclusão para componentes compartilhados; verificar que a etapa 05 mantém o comportamento vigente em testes de componente.
- [ ] 4.2 Criar `/admin/clients` com busca, paginação, cadastro, cards de vínculos/histórico e estados vazio/carregando/erro/sucesso; verificar funcionamento sem nenhuma galeria em desktop e smartphone.
- [ ] 4.3 Adicionar `Clientes` à navegação administrativa com estado ativo e acesso por teclado; verificar rota direta, menu responsivo e sessão não administrativa negada pelo backend.
- [ ] 4.4 Manter clientes vinculadas no bloco `Cadastro existente`, exibindo `Já vinculada` e edição sem ocultá-las; verificar atualização cruzada entre diretório global e etapa 05.
- [ ] 4.5 Exibir confirmação única com inventário e atualizar a lista imediatamente após exclusão; quando houver histórico, explicar o bloqueio e oferecer edição/desvinculação sem botão inoperante.

## 5. PIX global e checkout no backend

- [x] 5.1 Implementar leitura administrativa sanitizada da configuração PIX global e normalização de CPF, telefone, e-mail e BR Code reutilizando o módulo existente; verificar QR, recebedor, cidade, instruções e mensagens de erro.
- [x] 5.2 Implementar desafio e confirmação de criação, alteração e remoção do PIX com senha atual, OTP WhatsApp, sessão/conteúdo vinculados, expiração, rate limit e auditoria; verificar sucesso, OTP inválido, replay, payload trocado e canal indisponível.
- [x] 5.3 Alterar o contrato de Vendas para retornar PIX global somente leitura e rejeitar escrita PIX por galeria, preservando preço, tabela, prazo, mensagem, favoritas e comentários; verificar compatibilidade controlada com frontend antigo durante o rollout.
- [x] 5.4 Resolver somente PIX global `active` no novo checkout e congelar todos os campos no pedido; verificar configuração alterada, ausente e `review_required` sem perder a seleção.
- [x] 5.5 Preservar leitura de pedidos e pagamentos antigos a partir dos snapshots e dados legados necessários ao rollback; verificar pedidos criados antes da migration e ausência de recálculo.

## 6. Configuração PIX e etapa 02 no frontend

- [x] 6.1 Adicionar painel PIX global em Configurações com estado, prévia, validação e fluxo em duas etapas de senha + OTP; verificar foco, erros, expiração, cancelamento e confirmação acessível.
- [x] 6.2 Remover os campos editáveis PIX da etapa 02 e apresentar resumo somente leitura, QR e atalho para Configurações; verificar que `Salvar e avançar` persiste todas as demais regras.
- [x] 6.3 Exibir avisos acionáveis para PIX ausente ou divergência legada sem bloquear a preparação da galeria; verificar que o checkout permanece indisponível e a seleção preservada.
- [x] 6.4 Atualizar cliente HTTP, tipos e testes de contrato para versões/estados globais sem transportar chave PIX em superfícies não autorizadas.

## 7. Integração, segurança e entrega

- [ ] 7.1 Executar integração sintética completa: criar cliente, vincular/privatizar sem compra, excluir imediatamente, preservar outra cliente; repetir com pedido para comprovar bloqueio e histórico.
- [x] 7.2 Executar integração PIX: migrar configuração, confirmar nova versão, abrir pedidos antes/depois da troca e comprovar snapshots distintos e imutáveis; testar ausência/divergência e rollback da aplicação.
- [x] 7.3 Executar Ruff e suíte backend completa, lint/typecheck/testes/build frontend, migrations em PostgreSQL descartável, OpenSpec estrito, gitleaks e `git diff --check`; corrigir regressões relacionadas antes de marcar.
  - Evidência 2026-09-06/07: Ruff e backend completo aprovaram `364 passed, 1 skipped`; frontend aprovou 147 testes, typecheck e build, com lint sem erros; migration teve quatro cenários PostgreSQL; OpenSpec estrito aprovou 28/28, gitleaks e `git diff --check` não apontaram achados. O CI final `34073819354` reconfirmou backend, frontend, OpenSpec e gitleaks verdes.
- [ ] 7.4 Documentar contratos, lifecycle de exclusão, configuração PIX, compatibilidade, operação e rollback para continuidade entre executores; confrontar documentação com specs e código.
- [x] 7.5 Preparar inventário zero-impact de homologação com SHA, migration, serviços/portas, dados sintéticos e rollback; não executar migration, excluir o cliente relatado nem fazer deploy sem nova autorização humana explícita.
  - Evidência 2026-09-06/07: antes das mutações foram registrados projeto/Compose exclusivos, SHA, migration, containers, volumes, porta única `127.0.0.1:8080`, subdomínio, recursos ARM, estado facial e inventário de dados/mídia; backup lógico e rollback ficaram definidos. Deploy e limpeza ocorreram somente após autorização explícita.
- [ ] 7.6 Após deploy autorizado, confirmar migration no head, paridade do SHA, healthchecks, cliente sintético removível, diretório sem galerias e PIX global em desktop/mobile; não sincronizar nem arquivar antes do aceite humano.
  - Parcial 2026-09-06/07: o run final `34073819354` e os deployments `6300430858`/`6300438039` ficaram verdes no SHA `07aa6dffdcbeb70e3a0f7eba91cc66dfaa150961`; migration `20260906_0046 (head)`, `/healthz` e `/api/health` foram confirmados. A limpeza autorizada preservou administrador/configurações/WhatsApp e deixou zero clientes, galerias, fotos e pedidos. Falta somente a conferência humana autenticada do PIX global em desktop/mobile e, quando o lifecycle de clientes for implementado, seu cenário sintético de exclusão.
