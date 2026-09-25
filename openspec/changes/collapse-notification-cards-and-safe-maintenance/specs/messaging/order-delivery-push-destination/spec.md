# Spec Delta

## Purpose

Garantir que o navegador aceite o destino autenticado das notificações de entrega de fotos já produzido pelo servidor, preservando a restrição a rotas internas conhecidas.

## ADDED Requirements

### Requirement: Destino de compras aceito pelo service worker

O transporte backend SHALL aceitar o destino de entrega válido `/library/purchases#order-UUID`. O service worker SHALL exibir esse push e navegar para esse destino ao clicar. Ambos SHALL aceitar a rota `/library/purchases` e seu fragmento opcional com UUID canônico, sem aceitar query strings, fragmentos arbitrários ou destinos externos. A autorização de acesso ao pedido SHALL continuar no backend.

#### Scenario: Push de entrega e clique
- **WHEN** o navegador recebe payload válido de entrega com destino `/library/purchases#order-UUID`
- **THEN** exibe a notificação e abre ou foca a aba da mesma origem no destino do pedido

#### Scenario: Destino adulterado
- **WHEN** o payload contém URL externa, query string, UUID malformado ou fragmento diferente de `order-UUID`
- **THEN** o service worker rejeita o payload e não abre o destino
