## Context

Ver proposal.md. Investigação somente leitura do checkout:

- `frontend/app/library/page.tsx`, `LibraryOrderCard`, usa `photo.preview_url` diretamente em miniatura/ampliação. `backend/app/main.py` devolve caminhos `/library/history/items/{id}/preview` ou `/gallery/{id}/photos/{id}/preview`; a aplicação expõe o backend via `/api`. Isso demonstra uma inconsistência concreta de encaminhamento, mas ainda não comprova o status HTTP do item real da captura. Não afirmar perda de arquivo nem modificar mídia real sem diagnóstico.
- A rota histórica verifica sessão cliente e propriedade do item. Preservá-la; não trocar por rota administrativa ou original.
- `frontend/app/admin/galleries/client-gallery-card.tsx` já concentra cards da pública e aceita ações. A privada renderiza cards em `[galleryId]/page.tsx`. `admin/payments/page.tsx` possui ações e capacidades `can_decide`/`can_correct`; reaproveitar seu fluxo, não criar outro motor financeiro.
- A biblioteca exibe somente a data em alguns cards. A galeria privada condiciona o prazo a carrinho não vazio, seleção aberta e ausência de pedido pendente. Não há contador nesse trecho. A regra de `fix-client-deadline-and-watermark-size` materializa duração padrão da pública em data absoluta ao criar privada: isso não é vencimento global de todas as clientes.
- Mudanças operacionais anteriores de push/branding permanecem em arquivos locais próprios; não misturar seus registros pendentes com esta implementação.

## Goals / Non-Goals

**Goals:** corrigir contratos de mídia, reutilizar controles financeiros e tornar o prazo efetivo perceptível, com projeções mínimas e componentes compartilhados.

**Non-Goals:** recalcular datas existentes, apagar/regerar mídia em massa, mudar retenção ou autorização, criar prazo global novo, expandir catálogo de notificações, disparar mensagens de teste reais, alterar infraestrutura/secrets ou reimplementar pagamentos.

## Decisions

1. **Resolver caminhos de mídia no limite de apresentação compartilhado.** Usar o padrão existente de URL do backend sob `/api` para miniatura/ampliação, sem duplicar prefixo em caminhos já normalizados nem aceitar URL externa/arbitrária. Cobrir caminhos históricos e operacionais. Não mudar todas as URLs serializadas do backend, pois outros consumidores já acrescentam `/api`; não remediar com proxy público de fotografias. Exibir fallback curto para falha real, preservando nome/quantidade do pedido. Verificar uma resposta de imagem, não só a presença de `img` em teste.
2. **Componente/controlador de ação financeira reutilizável.** Extrair o mínimo das ações de Vendas e pagamentos para uso ali e nos cards. Usar IDs de pedido/comunicação e capacidades autoritativas, confirmação explícita com cliente/galeria/valor, bloqueio de duplo clique, tratamento de conflito e refresh localizado após decisão. Para vários pedidos, mostrar linhas/resumo por pedido ou uma escolha compacta dentro do card; nunca confirmar pelo status agregado da cliente. Não navegar o fotógrafo para um dashboard genérico nem carregar esse dashboard inteiro por card. Novas projeções, se necessárias, devem ser agrupadas por consulta/página e estritamente administrativas.
3. **Prazo compartilhado, sem nova regra de expiração.** Propagar data efetiva pelas projeções existentes onde faltar. Mostrar na galeria de seleção e jornada da biblioteca; no admin, ficha privada e cards da pública/privada. Não colocar prazo de seleção no card de compra como vencimento do pedido. Renderizar data/hora em pt-BR com fuso explicitável pelo navegador e restante compacto: dias/horas, horas/minutos ou menos de um minuto. Atualizar pelo relógio local no máximo a cada minuto e ao retornar à aba, sem polling de rede por card; no vencimento/refoco, revalidar estado de seleção pela consulta existente. Backend continua autoridade, inclusive contra relógio local incorreto. Ausência de data mostra apenas padrão configurado quando pertinente; sem contagem inventada. Data alterada no servidor substitui a anterior na próxima atualização normal.
4. **Compatibilidade e desempenho.** Manter os dois domínios (seleção e compra) separados. Extrações de componentes não alteram contratos financeiros; correção permanece silenciosa em ambos os canais. Nenhuma migration prevista. Se surgir necessidade de alteração destrutiva/retenção/política, registrar e pedir revisão, não improvisar.

### Refinamentos confirmados durante a implementação

- Compras sucessivas são decisões independentes. A projeção lista todos os pedidos comunicados, prioriza revisão pendente e ordena cada grupo do mais recente ao mais antigo. Confirmação anterior nunca abrange novas fotos. Havendo mais de uma comunicação no mesmo pedido, o atalho usa a comunicação mais recente, como Vendas e pagamentos.
- `payment_capabilities` concentra os gates de apresentação já existentes; endpoints de decisão/correção e suas transações não foram alterados. Resposta idempotente HTTP 200 com estado diferente da decisão solicitada também é apresentada como estado atualizado, não como confirmação bem-sucedida daquela ação.
- O prazo aparece também na Galeria pública autenticada quando existe privada operacional. A primeira seleção devolve a data efetiva na própria resposta, inclusive a seleção pelo resultado facial; evita recarregar a grade e interferir em seleção/favoritos. Nenhuma data é criada no frontend.
- A biblioteca agrupa revalidações simultâneas dos contadores em uma consulta; o relógio atualiza no máximo por minuto, e retorno à aba/vencimento revalida pelas consultas existentes. O backend continua bloqueando seleção/checkout fora do prazo.
- Prévia dos templates financeiros nos cards é carregada somente ao expandir o controle, com atalho explícito para edição global em Notificações. Não se consulta o dashboard financeiro por cliente.

## Risks / Trade-offs

- Prévia pode ter também arquivo ausente ou autorização inválida → primeiro testar URL/autorização e resposta; não mascarar falha só com placeholder. Reparo de arquivo real fora do fix de roteamento exige escopo comprovado/autorizado.
- Estado agregado não identifica comunicação → incluir identificação/capacidades por pedido na projeção, sem N+1 nem seleção implícita do primeiro pedido.
- Um pedido confirmado pode coexistir com nova seleção → prazo refere-se a novas seleções; status e histórico do pedido não mudam.
- Relógio da aba/fuso/hidratação → testes com relógio controlado, datas UTC, retorno à aba e vencimento; nenhum timer local concede autorização.
- Ação financeira pode gerar mensagem real → testes com transportes simulados e fixture isolada. Aceite humano remoto controla eventos reais.

## Migration Plan

Revisão humana destes artefatos precede código. Criar branch própria a partir do `develop` vigente preservando mudanças locais anteriores. Validar apenas testes pertinentes, lint/typecheck/build aplicáveis e OpenSpec. Antes do push revisar diff e excluir `.codex-tmp`, arte e registros de outra change. Depois do push, encerrar o turno para o proprietário acompanhar Actions (não monitorar nem criar automação). Merge/deploy conforme autorização e inventário específico; não alterar chaves push recém-ativadas. Verificação humana da compra reportada e dos cards depois de deploy autorizado; sem sync/archive antes desse aceite. Rollback apenas de código via fluxo seguro, sem apagar compras, prévias ou datas.
