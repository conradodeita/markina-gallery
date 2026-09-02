## 1. Baseline e reconciliação do domínio

- [x] 1.1 Mapear modelos, rotas, serviços, páginas e testes que ainda usam proprietária exclusiva, clonagem por cliente, convite privado individual ou preço por volume, e verificar o inventário com busca reproduzível registrada nas notas desta change.
- [x] 1.2 Criar testes de caracterização para snapshots comerciais, remoção operacional, links legados e isolamento atual por `client_id`, e verificar que passam antes da mudança estrutural.
- [x] 1.3 Atualizar fixtures/factories para representar uma privada com múltiplos membros sem remover os cenários legados, e verificar que a suíte consegue construir ambos os estados.

## 2. Associação multiusuário e migração aditiva

- [x] 2.1 Implementar o modelo `DerivedGalleryMembership`, estados e índices compostos, mantendo `DerivedGallery.client_id` como proprietária legada somente leitura, e verificar metadados SQLAlchemy e constraints em teste.
- [x] 2.2 Criar migration Alembic aditiva para associação, chave de origem e campos de compatibilidade, com pré-diagnóstico de duplicidade e backfill idempotente de cada proprietária atual, e verificar upgrade sobre banco vazio e fixture legada.
- [x] 2.3 Fazer a migration abortar antes da constraint quando encontrar mais de uma privada para o mesmo par origem/cliente, produzindo diagnóstico sem mesclar histórico, e verificar com teste de migration conflitante.
- [x] 2.4 Implementar serviço transacional para criar, reutilizar, bloquear, desbloquear, desvincular e reativar associação, resolvendo corrida pela constraint do banco, e verificar testes concorrentes/idempotentes.
- [x] 2.5 Substituir autorização operacional baseada em `DerivedGallery.client_id` pela associação ativa, preservando acesso histórico por pedido, e verificar matriz de acesso para membro ativo, bloqueado, desvinculado, terceiro e administrador.

## 3. Links estáveis, OTP e notificações

- [x] 3.1 Implementar assinatura e validação HMAC versionada para capacidades reconstruíveis com segredo dedicado validado no startup, sem persistir token ou assinatura em claro, e verificar rotação, adulteração, segredo ausente e expiração em testes.
- [x] 3.2 Estender schema e serviço de capacidades para link privado reutilizável sem cliente pré-vinculada, preservando leitura de links legados até expiração/revogação, e verificar migration e compatibilidade de contratos.
- [x] 3.3 Implementar endpoints administrativos para obter/copiar, revogar e regenerar links públicos e privados, retornando estado explícito quando um token legado não puder ser reconstruído, e verificar que regeneração invalida o endereço anterior sem remover membros.
- [x] 3.4 Exigir OTP contextual para todo vínculo novo aberto por sessão existente ou anônima, reutilizando a identidade única por telefone E.164, e verificar que vínculo já autorizado retoma sem desafio e nova origem exige desafio.
- [x] 3.5 Fazer a confirmação de link privado associar a cliente à privada e à origem pública, convergir para o vínculo existente no mesmo pai e manter bloqueio, e verificar cenários de dois links concorrentes, privada conflitante e tentativa de contorno.
- [x] 3.6 Implementar endpoints administrativos de membros com listagem, inclusão, bloqueio, desbloqueio e desvinculação sem apagar cliente ou histórico, e verificar respostas e auditoria para cada transição permitida e inválida.
- [x] 3.7 Gravar eventos idempotentes de criação de privada e mudança de membro na outbox e disponibilizá-los no painel, deixando canal externo assíncrono, e verificar repetição de requests/jobs e falha sanitizada do adaptador.
- [x] 3.8 Executar testes negativos de privacidade em todos os contratos de cliente para comprovar que membros, telefones, seleções, comentários, pedidos e notificações de terceiros não são serializados.

## 4. Preço progressivo e PIX no backend

- [x] 4.1 Implementar modelos e migration de presets globais versionados, faixas, modo comercial e snapshot por Galeria pública, e verificar constraints de código único, contiguidade, última faixa ilimitada e preços não crescentes.
- [x] 4.2 Migrar uma faixa legada para preço fixo e marcar múltiplas faixas como `legacy_volume` sem recalcular pedidos, e verificar upgrade com fixtures dos dois formatos e snapshots históricos imutáveis.
- [x] 4.3 Substituir a cotação de faixa única por cálculo progressivo em parcelas com detalhamento e economia, e verificar unitariamente os limites, 60 fotos por R$ 390,00, quantidade inválida e faixa ilimitada.
- [x] 4.4 Implementar CRUD/listagem/desativação de presets e endpoint autoritativo de simulação, e verificar versionamento, rótulo `código — nome`, snapshots imutáveis e rejeição de payload parcial.
- [x] 4.5 Adaptar configuração comercial da Galeria pública para escolher preço fixo ou preset progressivo e exigir conversão explícita de `legacy_volume`, e verificar que alteração global posterior não afeta a galeria.
- [x] 4.6 Tornar `copy_paste` a fonte única do PIX, validar o código e gerar QR localmente; migrar `qr_code_payload` somente quando seguro e sinalizar divergência, e verificar casos vazio, equivalente, divergente e malformado.
- [x] 4.7 Fazer simulador, checkout e criação de pedido usarem o mesmo serviço de cotação, congelando parcelas, economia, PIX e termos no pedido, e verificar idempotência e ausência de recálculo após alteração da galeria.

## 5. Acervo privado, estado individual e lifecycle

- [x] 5.1 Adaptar derivação manual e administrativa para criar/reutilizar a associação única da origem, adicionar referência ao acervo comum e criar seleção somente para o membro solicitante, e verificar fotos de pessoas diferentes no mesmo total.
- [x] 5.2 Garantir que nova referência por administrador ou membro apareça para todos os membros ativos sem copiar mídia nem propagar favorito/seleção/compra, e verificar checksums/storage keys e estados de duas clientes.
- [x] 5.3 Adaptar favoritos, visualizações, comentários, seleção, checkout e pagamento para filtrar sempre por associação e `client_id`, e verificar que duas clientes podem comprar a mesma foto com históricos independentes.
- [x] 5.4 Adaptar DTOs administrativos para membros paginados e contagens agregadas sem N+1, mantendo contratos legados necessários na janela de compatibilidade, e verificar quantidade de queries e snapshots de resposta.
- [x] 5.5 Adaptar biblioteca e DTOs de cliente para mostrar cada origem e sua única privada, além do histórico autorizado após bloqueio/remoção, e verificar roteamento com uma e várias origens.
- [x] 5.6 Atualizar inventário e execução de exclusão pública/privada para contar associações e capacidades, revogar acesso e preservar pedidos, manifestos e entregas, e verificar dry-run, execução idempotente e mídia histórica.
- [x] 5.7 Manter `derive_approved_facial_result` não exposto e indisponível, aceitando apenas a origem interna `facial` para integração futura aprovada, e verificar que nenhuma rota biométrica foi criada e o teste do gate continua verde.

## 6. Área administrativa

- [x] 6.1 Ler a documentação local da versão instalada do Next.js para App Router, mutations, navegação e fontes antes de editar o frontend, e registrar no artefato a versão e os arquivos consultados.
- [x] 6.2 Criar tela administrativa de tabelas globais progressivas com código, nome, faixas, validação em BRL, edição versionada e desativação, e verificar fluxos desktop/mobile e testes de formulário.
- [x] 6.3 Refazer a etapa 02 para alternar entre preço fixo e dropdown `código — nome`, simular parcelas/economia e configurar somente PIX copia-e-cola, e verificar recarga, erro de backend, `legacy_volume` e QR.
- [x] 6.4 Unificar `Salvar e avançar` nas etapas editáveis e proteger troca direta/retorno com estado sujo, e verificar testes de sucesso, falha, clique repetido e descarte confirmado.
- [x] 6.5 Completar a etapa 05 com links públicos/privados estáveis, copiar, regenerar, criação administrativa de privada e membros com bloqueio/desbloqueio/desvinculação, e verificar estados vazios, carregamento, erro e conflito.
- [x] 6.6 Atualizar resumo da Galeria pública e detalhe da privada com miniaturas, pastas navegáveis, upload/remoção autorizados e cards individuais de selecionadas, compradas, pagamento e prazo, e verificar que agregados pertencem à cliente correta.
- [x] 6.7 Ampliar o registro tipado de fontes locais para no mínimo oito opções, incluindo três manuscritas, validar IDs no backend e aplicar preview de capa, e verificar build sem fonte remota e fallback acessível.
- [x] 6.8 Adicionar notificações administrativas de privada/membro com leitura e filtros básicos sem enfileirar mensagens soltas, e verificar idempotência visual e ausência de dados comerciais de terceiros.

## 7. Portal da cliente

- [x] 7.1 Adaptar entrada por links e OTP ao novo contrato contextual, incluindo telefone brasileiro com `+55` e nono dígito sem duplicar identidade, e verificar vínculo público, privado, conflito, bloqueio e retorno autenticado.
- [x] 7.2 Adaptar biblioteca e visualização da privada compartilhada para acervo comum com marcadores individuais, grade responsiva e prévias protegidas, e verificar duas sessões de cliente em desktop e mobile.
- [x] 7.3 Implementar rodapé flutuante com quantidade, parcelas, total, economia e `Prosseguir` usando exclusivamente a cotação do backend, e verificar fotos de pessoas diferentes e atualização após adicionar/remover seleção.
- [x] 7.4 Implementar conferência com miniaturas, nomes, PIX copia-e-cola, QR e ação idempotente `Informar pagamento`, e verificar estado `em análise`, clique repetido, confirmação e pedido complementar.
- [x] 7.5 Garantir que somente a cliente do pedido veja valores, pagamento e histórico e receba confirmação personalizada, e verificar testes end-to-end com dois membros da mesma privada.
- [x] 7.6 Manter busca facial indisponível na interface até conclusão do spike e change própria, e verificar que nenhum upload, consentimento ou promessa de resultado aparece em build de produção.

## 8. Qualidade, documentação e entrega

- [x] 8.1 Executar testes backend direcionados e suíte completa, lint e verificação Alembic de head único; corrigir regressões da change e registrar comandos/resultados verificáveis.
- [x] 8.2 Executar testes frontend direcionados e suíte completa, lint, typecheck e build; corrigir regressões da change e registrar comandos/resultados verificáveis.
- [x] 8.3 Executar teste de integração do ciclo completo com dados sintéticos: link, OTP, vínculo, privada multiusuário, isolamento, seleção, cotação progressiva, pedido, pagamento e histórico após lifecycle.
- [x] 8.4 Revisar o diff integral contra proposal, design e deltas, confirmar ausência de segredos/fontes remotas/biometria e validar esta change com `npx --yes @fission-ai/openspec validate consolidate-shared-private-galleries-and-progressive-sales --strict`.
- [x] 8.5 Preparar inventário de homologação com SHA, migrations, containers/portas/subdomínio, secrets requeridos e plano zero-impact; verificar que nenhuma ação toca recursos de terceiros e solicitar autorização explícita antes de migration/deploy.
- [ ] 8.6 Após autorização específica, aplicar migration e deploy em homologação sem prune/down, confirmar SHA implantado, head Alembic, `/healthz`, `/api/health` e smoke tests do ciclo sintético.
- [ ] 8.7 Submeter a experiência desktop/mobile à revisão humana em homologação, registrar bugs e evidências e manter esta task aberta até aprovação explícita.
- [ ] 8.8 Após aprovação humana, sincronizar as specs principais, reconciliar checkboxes supersedidos das changes relacionadas e arquivar somente as changes efetivamente completas; verificar `openspec status` e validação estrita final.
