# Proposal

## Why

A jornada de cadastro foi provada por teste de navegador, mas encerra os serviços ao final e não permite ao proprietário experimentar a UI. O backend mantém corretamente e-mail/anti-bot reais indisponíveis. É necessário um ambiente de demonstração local persistente e sintético.

## What Changes

- Criar um executor opt-in somente local, vinculado a loopback, com PostgreSQL descartável exclusivo e migration de destino explícita.
- Injetar adaptadores sintéticos de código de e-mail e anti-bot somente nesse processo; expor os códigos gerados em uma caixa de testes local.
- Permitir cadastro e login como fotógrafo tenant pela UI existente, sem alterar rotas de produto nem abrir cadastro em produção.
- Documentar inicialização, acesso e encerramento dos recursos próprios da demonstração.

## Impact

O escopo inclui a ferramenta de demonstração, documentação, testes locais e um ajuste CSS isolado ao formulário de cadastro existente. Não altera rotas nem o comportamento de cadastro em produção. Nenhum provedor externo, domínio público, conta operacional ou configuração de produção será usado. A avaliação de refatoração fica restrita ao runner novo; não há fluxo de produto substituído.
