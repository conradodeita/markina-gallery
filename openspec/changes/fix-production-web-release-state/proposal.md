# Proposal

## Why

A auditoria do PR #226 comprovou que o fluxo app substitui o web sem atualizar sua identidade consumida pelo fluxo web-only. O inventário web escreve no lock e a recuperação pode selecionar uma versão histórica incorreta. Precisamos corrigir estes contratos antes da publicação de segurança, sem operar a Oracle.

## What Changes

- Registrar identidade web por commit, ID Docker, hash Compose e checkout de referência, compartilhada pelos dois fluxos.
- Exigir adoção explícita e auditada do runtime legado, com ID/commit conferidos em evidência externa; marcadores antigos serão apenas históricos.
- Tornar inventários app/web sem escrita, sem fetch, temporários ou aquisição de lock; exigir objetos locais obtidos em preparação autorizada.
- Conferir escopo, imagens e aprovação antes de qualquer mutação; usar lock existente aberto somente para leitura nos fluxos mutáveis.
- Preservar imagens por ID, validar recuperação e manter registro durável de tentativa interrompida. Recuperação web contingencial requer o mesmo gate de aprovação, sem tocar outros serviços.
- Cobrir transições, concorrência, falhas e ausência de escrita em testes sintéticos. Integrar somente se classificador e workflows comprovarem ausência de operações remotas.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: identidade web entre fluxos, inventário sem escrita, preservação por ID e recuperação auditável.

## Impact

Somente scripts, testes, runbooks e OpenSpec; sem mudança funcional, Dockerfile, Compose, dependências ou dados. Baseline de produção e gates protegidos ficam inalterados. A autorização desta fase abrange desenvolvimento/GitHub; toda escrita Oracle aguarda aprovação específica posterior. O pin do wrapper app deve acompanhar seu conteúdo no repositório, mas sua instalação remota não está autorizada nem é pré-requisito para o fluxo web manual.

## Correção pontual após execução bloqueada

A execução autorizada do SHA 34d2afd5 terminou antes da adoção: o snapshot inclui corretamente o migrate histórico parado, mas seu acesso direto a .State.Health falha quando a chave opcional falta. A retomada de engenharia autorizada limita-se a esse acesso, regressões com Docker CLI real e atualização dos pins derivados. Nenhum container será omitido/removido para contornar o erro; nenhuma escrita Oracle está autorizada para o novo SHA.
