# Proposal

## Why

Após a unificação das galerias, o fotógrafo precisa distinguir somente entrada livre pelo link autenticado e entrada previamente autorizada. `Coletivo protegido` bloqueia toda a navegação, inclusive pastas atribuídas, e sua explicação sobre reconhecimento facial confunde modo de acesso com processamento biométrico.

## What Changes

- Oferecer somente `Padrão` (`standard`) e `Somente convite individual` (`invite_only`) na criação e edição de galerias; manter `invite_only` como padrão inicial.
- **BREAKING**: recusar `collective_protected` em novas criações e alterações explícitas de modo pela API administrativa.
- Explicar que Padrão permite cadastro/vínculo pelo link válido após OTP, enquanto Somente convite individual exige vínculo prévio ou convite individual autorizado. Nos dois modos, a cliente vê pastas comuns e apenas as exclusivas atribuídas a ela.
- Preservar registros antigos `collective_protected` e sua negação de navegação; nenhuma migration ou salvamento de outro campo deve convertê-los. Uma mudança para um dos dois modos exige escolha explícita do fotógrafo, com aviso contextual sobre a mudança de acesso.
- Preservar OTP, vínculos, público das pastas, seleções, pedidos, histórico, notificações e todos os gates faciais. Remover a explicação facial enganosa da seção de modos.
- Atualizar mandato, roadmap e contexto OpenSpec para distinguir os dois modos operacionais da compatibilidade protegida legada.
- Acrescentar `Pagamento obrigatório?` na etapa 2. Marcado, exige valor unitário positivo; desmarcado, permite finalizar e congelar a seleção sem PIX, cobrança ou pagamento pendente, ocultando preços e totais da cliente.
- Manter exportação e entrega posterior pelo fotógrafo para seleções finalizadas, com histórico em Compras identificado como seleção, sem registrar pagamento confirmado ou receita.
- Corrigir a ausência de `Mensagem comercial` na revisão da cliente, exibindo o texto correspondente a cada galeria nos dois modos de pagamento.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `client-access/cloned-private-galleries`: entrada por dois modos operacionais, público de pastas independente e preservação de modo protegido legado.
- `gallery-sales/operational-gallery-interface`: dois modos de entrada, configuração de pagamento obrigatório, operação da seleção sem cobrança e apresentação da mensagem comercial à cliente.

## Impact

Backend: validação administrativa, configuração persistida de cobrança, finalização idempotente, histórico e autorização de entrega. Frontend: editor, coleção, carrinho e Compras. Documentação: OpenSpec, mandato e roadmap. Migration aditiva para configuração e snapshots, preservando o modo de cobrança existente; sem conversão em massa de pedidos, exclusão de dados, reprocessamento facial ou configuração de servidor. A branch de planejamento parte do PR documental #107; integrar a base antes do PR de implementação.
