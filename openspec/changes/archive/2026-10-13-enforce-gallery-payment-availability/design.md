# Design

## Context

Ver `proposal.md`. Base isolada em `0ef80fd`, em worktree própria; o checkout original do usuário permanece com suas alterações locais.

Evidências da investigação:

- `backend/app/main.py`, `update_parent_gallery_sales`, valida precificação e persiste `payment_required`, sem exigir meio disponível.
- `backend/app/unified_checkout.py` calcula cartão por tenant, configuração ativa/pronta e `card_enabled`; a elegibilidade comercial não constitui prova de disponibilidade de PIX.
- `frontend/app/library/cart/page.tsx` começa com `method="pix"` e tenta preparar PIX automaticamente; grupos com `payment_required=false` oferecem `Finalizar seleção`, fora do bloco financeiro.
- `frontend/app/admin/settings/pix-panel.tsx` permite `configuration=null` e exibe `Remover PIX`.
- A sessão autenticada em `markina.pickyourpic.com.br/admin/settings` mostrou PIX configurado e cartão desligado. A edição existente exibe o checkbox individual de cartão, desmarcado. Nenhuma configuração foi salva.

## Goals / Non-Goals

**Goals:** reutilizar a autoridade por conta para validar meios na configuração, disponibilização e checkout; assegurar que troca de recebedor seja atômica e sem intervalo de indisponibilidade.

**Non-Goals:** criar novo controle de cartão, obrigar recebimento em galerias de seleção externa, consultar InfinitePay para validar cada leitura, confirmar pagamento real, modificar webhook, expirar/cancelar link externo, migrar dados reais, limpar ou publicar.

## Decisions

### Mínimo de um meio, definido pela jornada

O esclarecimento mais recente fixa a exigência na galeria paga. Preservar o contrato `PIX ausente e cartão utilizável` de `add-infinitepay-credit-payments`; interpretar PIX como padrão entre meios utilizáveis, sem inventar um código inexistente. A confirmação anterior de permitir apenas substituição de PIX existente continua aplicada à configuração: criação e substituição permanecem; remoção explícita deixa de existir. Desmarcar cobrança da galeria apenas retira a etapa da cliente e não apaga a chave da conta.

`simplify-gallery-access-modes` continua autoridade de preços positivos, snapshot e finalização sem cobrança. O delta desta change acrescenta validação de recebimento, não reescreve nem sincroniza a change anterior. A regra consolidada que permitia salvar vendas sem PIX fica condicionada a cartão utilizável ou modo sem cobrança.

### Capacidade efetiva compartilhada e sem chamada externa

Reutilizar validações locais do PIX e perfil/habilitação InfinitePay para projetar `pix_available`, `card_available` e meios efetivos por tenant. Não confundir meio configurado com pagamento aprovado. Aplicar a mesma projeção ao editor, salvamento comercial, disponibilização e preparação escolhida. Revalidar no servidor a cada mutação; parâmetros de frontend não concedem disponibilidade.

Permitir criar rascunho antes de cadastrar recebimento, pois `payment_required` já inicia verdadeiro; impedir salvar/avançar a etapa paga e nova disponibilização sem meios. Galerias antigas incompatíveis mantêm seus dados e seleções e apresentam orientação recuperável; não as converter automaticamente para seleção externa.

### Substituição protegida e manutenção do último meio

Rejeitar `configuration=null` antes de emitir desafio PIX e novamente na confirmação, para alcançar desafios antigos. Enquanto aguardam senha/OTP da substituição, dados atuais continuam ativos. Manter controle de versão/locks existentes e snapshots de pedidos.

Na configuração InfinitePay, recusar mudança que retiraria o único meio de galerias pagas já disponibilizadas. Fotografias, reservas e links antigos seguem a autoridade existente; desligar oferta não cancela link remoto. A guarda considera a conta autenticada e precisa ser serializada com disponibilização/configuração para não admitir dois caminhos concorrentes que removam a última capacidade.

Fronteira adicional identificada na aplicação: reativação por `PATCH /admin/parent-galleries/{id}/settings` pode expor pastas já liberadas. Essa transição entra na mesma guarda/ordem de lock. Galerias em exclusão ainda reversível conservam proteção do último meio enquanto ativas, para que cancelar a exclusão não restaure uma jornada paga recém-desconfigurada. O tratamento não altera exclusão/restauração de dados.

A liberação adiada preserva também o contrato de indexação facial existente: após corrigir recebimento e publicar os derivados já prontos, reutilizar o gatilho idempotente de indexação. Ele conserva gates, escopo, políticas e filas existentes; não introduz outro motor nem ativa processamento. Sem esse evento, o caminho de prévias legado poderia perder a indexação porque a foto ainda não estava disponível na geração dos derivados.

### Checkout preparado conforme meio e grupos

Selecionar PIX inicialmente quando disponível. Se houver somente cartão utilizável, não preparar PIX antes de permitir cartão. A disponibilidade de um meio não libera fotos reservadas em tentativa externa existente. Grupo sem cobrança permanece independente, inclusive quando checkout pago tiver erro. Confirmar que o frontend realmente omite a seção financeira quando todos os grupos forem sem cobrança.

Alternativa rejeitada: esconder somente `Remover PIX` sem validação API. Outra alternativa rejeitada: exigir dados PIX de toda conta ou cobrar automaticamente uma seleção cujo pagamento não é obrigatório.

## Risks / Trade-offs

- [Bloqueio inesperado ao editar galeria paga legada sem recebimento] → erro específico, atalho de correção e preservação integral do estado; permitir preparação de rascunho e mudança explícita para seleção externa.
- [Apenas cartão disponível e remoção do último meio] → guarda por conta, transação e testes concorrentes PostgreSQL; não usar config de outra conta.
- [Desafio PIX de remoção emitido antes da publicação] → recusa também no endpoint de confirmação, sem consumir configuração vigente.
- [Checkout pendente não equivale a novo pedido] → preservar snapshots, URLs e reservas; meios novos não podem liberar cobrança incerta.

## Migration Plan

Não há migration de dados prevista. Implementar validações e projeções em branch `feature/*` após revisão humana, sem apagar ou fabricar configurações. Ensaiar regressões direcionadas e PostgreSQL sintético para isolamento/concorrência; depois executar checks aplicáveis no SHA final.

Deploy somente após autorização própria e inventário/portas/plano de impacto zero. Reversão de código não altera snapshots, mas reintroduziria remoção PIX e menor exigência comercial; registrar essa consequência. Sincronização e archive dependem de revisão humana.
