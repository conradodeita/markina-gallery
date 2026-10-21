# Tasks

## 1. Delimitação e contratos
- [x] 1.1 Confirmar os pontos afetados e distinguir o mínimo documentado do InfiniteTap da proteção local solicitada para o Checkout Integrado; registrar escopo e compatibilidade antes do código.

## 2. Mínimo antes da reserva
- [x] 2.1 Registrar regressões de total menor que 100, fronteira de 100, total válido com itens baratos e repetição histórica; implementar guarda backend antes dos efeitos e validar API/domínio e PIX preservado.
- [x] 2.2 Cobrir a orientação e o bloqueio de cartão no carrinho, preservando seleção, PIX e escolha de fotos; implementar e validar a UI.

## 3. Redirecionamento no primeiro clique
- [x] 3.1 Reproduzir ausência de navegação no primeiro clique e corrigir; cobrir URL válida, inválida, incerteza, erro, retomada e duplo clique sem enfraquecer idempotência.

## 4. Integração e entrega
- [x] 4.0 Preparar manifesto estrito dos três arquivos API/web e classificação a partir do baseline publicado21b89c3, com regressões de aceitação exata e recusa de adulteração/arquivos não listados; não incluir cofre/migration nem executar publicação. Evidência: política operacional aprovada,18 testes de escopo e14 de classificação aprovados; gate real sobre a4b950a retorna somente_api_web.
- [x] 4.1 Executar regressões pertinentes, lint, typecheck, build e OpenSpec; revisar diff e manutenção proporcional e registrar evidências e limites. Evidência:91 testes PostgreSQL e605 frontend aprovados; lint/build/TypeScript/Ruff/OpenSpec1.14.0 e gates locais aprovados; ver validation.md. CI remoto continua requisito separado.
- [ ] 4.2 Criar PR focado em draft com plano mínimo de publicação/rollback e verificar CI final do candidato; sem merge ou deploy nesta autorização.
