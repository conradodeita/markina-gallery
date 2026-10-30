# Tasks

## 1. Confirmar e documentar os gates existentes

- [x] 1.1 Conferir no código e nos testes que a conta live exige gate global ativo, configuração Mercado Pago ativa no tenant e credenciais com recebedor validado; executar somente os testes focados já existentes para esse contrato e registrar evidência. Evidência local em `validation.md`: 39 aprovados, 2 skips existentes.
- [x] 1.2 Conferir que conta de teste em ambiente operacional continua limitada ao par tenant/cliente e que retirar a permissão bloqueia novas emissões, mas preserva consulta e reconciliação; registrar evidência sem enviar pagamentos. Cobertura dos testes de operações/checkout; sem emissão externa.
- [x] 1.3 Reconciliar a documentação histórica do piloto para deixar claro que a restrição de cobrança real foi substituída por esta liberação, preservando as evidências e os resultados sandbox anteriores. Nota datada adicionada ao design e plano de release Orders.
- [x] 1.4 Limitar a resposta da comparação de ancestralidade do GitHub sem enfraquecer a prova `status`/base/merge-base; validar o parâmetro `per_page=1`, o tamanho de resposta e os casos fail-closed antes de repetir o inventário remoto. Implementado no helper Orders e coberto por teste de URL e resposta excessiva; 58 testes passaram (1 skip local esperado), política do workflow, Ruff, sintaxe Bash, OpenSpec estrito e diff passaram. O inventário remoto ainda depende do CI e da instalação protegida do novo pin, como parte da task 2.1.

## 2. Preparar e ativar a liberação geral

- [x] 2.1 Preparar e apresentar plano com SHA, serviços, portas, gate, matriz por tenant e recuperação antes da escrita. Concluído pela operação 04, suporte main `180de9e8`/CI `41010400151`, fingerprint atual e plano apresentados na conversa. A antiga recusa APP_ENV foi resolvida pelo corte conjunto autorizado; histórico e prova em validation.md.
- [x] 2.2 Ativar o gate live após autorização e verificar saúde/HTTPS sem cobrar. Fase separada enable-live concluiu com gate true; `/`, `/healthz`, `/api/health` 200, 10 serviços saudáveis e três faciais preservados/parados. Nenhuma cobrança emitida; ver validation.md.
- [x] 2.3 Confirmar disponibilidade por fotógrafo e preservar PIX/testes. Matriz real: um tenant com opt-in, PIX habilitado, uma conta sandbox restrita a um par, zero contas reais ainda configuradas e cofre verificado. Gate real aberto; cada fotógrafo precisa cadastrar sua conta válida pela UI. Detalhes em validation.md.
