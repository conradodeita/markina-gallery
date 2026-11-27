# Tasks

- [x] 1.1 Aplicar 30 dias a novos pedidos do fotógrafo, preservar pedidos legados, replays e retentativas e esconder seletores substituídos. Atualizar o modelo editável dos termos e a documentação vigente.
- [x] 1.2 Publicar progresso sanitizado por objetos verificados no fluxo existente e exibir uma barra acessível com fases e conclusão real. Cobrir integridade, falha sem débito e isolamento.
- [x] 1.3 Revisar o escopo e o código substituído, validar OpenSpec estrito, regressões dos contratos e build, e registrar evidência.

## Evidência local — 27/11/2026

- A suíte dirigida de cobrança, executor, termos, encerramento e console aprovou 80 casos na primeira execução. Dois testes novos de compatibilidade usavam uma preparação inválida de dados imutáveis. O reteste corrigido confirmou ambos e repetiu a prova do download, finalização e débito único, totalizando três testes aprovados nessa rodada.
- 15 testes de frontend passaram. O lint dos arquivos alterados teve zero erros e dois avisos preexistentes no mock de retentativa. Build e TypeScript do Next.js 16.4.5 passaram.
- Ruff, validação estrita OpenSpec e diff-check passaram. Removidos os seletores e CSS sem uso. O campo legado e as restrições dos registros históricos foram preservados. A infraestrutura local usou dados sintéticos; a produção e os termos publicados não foram acessados.
