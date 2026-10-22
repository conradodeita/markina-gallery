# Proposal

## Why

Após a publicação de `21b89c3` e CI #776 aprovado, o proprietário solicitou em 21/10/2026 dois ajustes: impedir novas emissões de cartão abaixo de R$ 1,00 e abrir o gateway no primeiro clique. A UI atual apenas salva a URL recebida e renderiza um segundo link; o backend aceita qualquer total positivo antes de reservar a seleção.

A regra explícita de R$ 1,00 e parcela mínima encontrada na fonte oficial pertence ao **InfiniteTap**, outro produto. As páginas oficiais consultadas do **Checkout Integrado** não explicitam esse limite. O piso solicitado será uma proteção local para novas compras por cartão, sem apresentar essa lacuna como contrato confirmado do provedor ou prova da causa de todas as falhas antigas.

## What Changes

- Validar o total de cartão de pelo menos 100 centavos antes de reservar fotos, invalidar rascunho PIX ou chamar o provedor.
- Orientar a cliente no carrinho abaixo do mínimo; permitir aumentar a seleção ou usar PIX manual quando configurado.
- Redirecionar na mesma aba assim que a primeira solicitação explícita retornar checkout utilizável; manter retomada por link se necessário.
- Preservar idempotência, bloqueio de resultados incertos, recuperação administrativa e compras existentes.

## Non-goals

Alterar preços, aplicar mínimo por foto ou ao PIX manual, definir parcelas no Pick-your-Pic, mudar API/autenticação, recuperar compras reais, publicar, mesclar PRs ou incluir o cofre do PR #262 e manutenção Python #261.

## Impact

Backend de reserva e frontend do carrinho, sem migration, segredo ou worker. Testes reutilizam PostgreSQL e transporte sintéticos. Nenhuma limpeza geral ou remoção de funcionalidade é necessária. Publicação futura exige revisão, CI, inventário e autorização próprios; a autorização do release concluído não cobre esta alteração.
