# Tasks

## 1. Preparação e contratos
- [x] 1.1 Registrar escopo de manutenção autorizado, evidência de legado e isolamento de produção.
- [ ] 1.2 Implementar coordenador de transição e recuperação testável, com recusa de gates incompletos.
- [ ] 1.3 Provar ordem e falhas com testes, incluindo fila ocupada, drift, lock e recuperação interrompida.

- [ ] 1.4 Rever proposta/design e aceitar os contratos de recuperação e impacto antes de implementar o novo comportamento.

## 2. Operação e homologação
- [ ] 2.1 Implementar/adaptar host operacional e inventário com proveniência Compose, journal e rollback por ID, sem migrations ou build Oracle.
- [ ] 2.2 Executar rehearsal real em ambiente descartável e documentar limites.
- [ ] 2.3 Revisar diff e executar OpenSpec, testes e gates aplicáveis; preparar PR para revisão quando coeso.

## 3. Gate externo
- [ ] 3.1 Obter tratamento/aceitação explícitos dos callbacks e autorização posterior da janela operacional. Não executar nesta preparação.

## Workflow follow-up
- Não sincronizar/arquivar sem revisão humana. Nenhum teste ou aceite de preparação autoriza execução na Oracle.
