## 1. Inventário e contrato
- [x] 1.1 Confirmar main e tentar o canal SSH existente somente leitura; registrar evidência atual ou bloqueio preciso.
- [x] 1.2 Registrar proposta, design e delta antes do código; reconciliar políticas ativas.

## 2. Classificação e isolamento
- [x] 2.1 Implementar impacto real por contexto, manifesto, imagem e serviço; classificar dependências sem deploy em push.
- [ ] 2.2 Provar isolamento/proveniência web e permitir manifests Python pendentes, preservando API/snapshot/rollback.

## 3. Operação protegida
- [x] 3.1 Gerar plano por grupo com inventário real, consumidores ativos/inativos, IDs/arquitetura e bloqueios de workers/executores.
- [x] 3.2 Disponibilizar coletor manual no SSH autorizado sem alterar pin, credenciais ou host; documentar saúde, backups e rollback.

## 4. Validação e integração
- [ ] 4.1 Testar frontend, Python, SHA misto, worker especializado e alteração protegida; negativos de proveniência/inventário e CI sem deploy.
- [ ] 4.2 Revisar diff/área afetada, executar testes de release, OpenSpec e Code Review; abrir PR e resolver CI.
- [ ] 4.3 Integrar infraestrutura somente após checks/revisões aprovados e acompanhar CI pós-merge sem operações de produção.
- [ ] 4.4 Repetir inventário somente leitura após integração; registrar cobertura e lacunas, sem declaração artificial de prontidão.
