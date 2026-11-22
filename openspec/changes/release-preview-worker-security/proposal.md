# Proposal

## Why
O worker de ajuste de prévias ativo conserva quatro versões anteriores às correções de segurança já integradas; API e worker principal estão corrigidos. O candidato ARM64 sobre a imagem exata passou na comparação de 60 distribuições e nos contratos HTTP/JPEG/PNG.

## What Changes
- Preparar manutenção controlada exclusiva dessa imagem, com pausa temporária dos produtores API/worker, drenagem e recuperação verificáveis.
- Acrescentar procedimento dedicado, com inventário, fingerprint, lock comum, journal durável, preservação e rollback por imagem; nenhum fluxo de migration é chamado.
- Provar cenários de sucesso/falha em ambiente isolado. Publicação Oracle depende de autorização posterior do proprietário.

## Capabilities

### New Capabilities
- Nenhuma.

### Modified Capabilities
- `deployment-operations`: manutenção isolada do worker legado de prévias.

## Impact
Scripts/testes/documentação. Na futura operação, somente a imagem do worker de prévias pode mudar. API/worker serão pausados e retomados nos mesmos containers; entrada pública ficará temporariamente em manutenção, afetando acesso, uploads e callbacks. Banco, Redis, frontend, imagens de outros serviços e modelos não serão publicados. A autorização recebida cobre preparação e testes, sem execução na Oracle.
