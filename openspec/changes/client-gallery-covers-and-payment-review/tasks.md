## 1. Experiência cliente
- [x] 1.1 Retirar ação de rejeição facial e validar seleção/favoritos/resultados. Evidência: 17 testes da página pública passaram.
- [x] 1.2 Projetar e renderizar capas autorizadas clicáveis na biblioteca; testar destino, ausência/falha e acesso. Evidência: 12 testes da biblioteca e teste backend com JPEG sintético/negativas passaram.
- [x] 1.3 Incluir prévias nos seletores de pastas e validar navegação, modo sequencial e mobile.

## 2. Correção financeira
- [x] 2.1 Estender endpoint/capacidades e UI para recusa; testar correção silenciosa, confirmação posterior, autorização, idempotência e PIX agrupado.

## 3. Entrega
- [x] 3.1 Executar regressões pertinentes, lint, typecheck/build frontend, validação OpenSpec e revisão do diff; registrar evidências e preparar PR. Evidências completas em `validation.md`.
- [x] 3.2 Corrigir bloqueio SQLite do teste de migração apontado pelo CI do PR #97, validar encerramento explícito da leitura e preparar a correção para o mesmo PR. Evidência: reprodução determinística antes do fix; arquivo completo com 10 testes aprovados e 1 PostgreSQL pulado após o fix; Ruff e OpenSpec aprovados.

Parar após push + PR para confirmação humana do CI. Sem deploy, mensagens reais, mudanças de `.env`, sync/archive ou inclusão de alterações locais anteriores nesta entrega.
