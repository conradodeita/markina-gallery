# Tasks

## 1. Preparação e contratos
- [x] 1.1 Registrar escopo de manutenção autorizado, evidência de legado e isolamento de produção.
- [x] 1.2 Implementar coordenador de transição e recuperação testável, com recusa de gates incompletos.
- [x] 1.3 Provar ordem e falhas com testes, incluindo fila ocupada, drift, lock e recuperação interrompida.

- [x] 1.4 Aplicar o escopo autorizado de preparação local, mantendo callback e janela operacional como gates sem aceite presumido.

## 2. Operação e homologação
- [x] 2.1a Implementar e testar o coletor read-only de inventário sanitizado, com proveniência Compose, identidade/arquitetura de imagens, estado de serviços e contagens agregadas.
- [x] 2.1b Implementar o adapter de pausa, drenagem, substituição, journal durável e rollback por ID, com overlays distintos para candidato e rollback e restauração exata da política de restart. Não reutilizar o executor da migration 0090. Validado localmente com testes sintéticos e ensaios isolados de Compose/Nginx; não executar contra Oracle.
- [x] 2.2 Executar rehearsal end-to-end em projetos Compose aleatórios e descartáveis; cobrir sucesso e recuperação após candidato incompatível, registrar limites do daemon compartilhado e remover somente recursos temporários pelo manifesto exato.
- [x] 2.3 Revisar o diff local e executar OpenSpec, testes, compilação e lint aplicáveis; registrar evidências e limites.
- [x] 2.4 Preparar PR draft de revisão após validar adapter operacional e rehearsal descartável (PR #351; sem merge).

## 3. Gate externo
- [ ] 3.1 Obter tratamento/aceitação explícitos dos callbacks e autorização posterior da janela operacional. Não executar nesta preparação.

## Workflow follow-up
- Não sincronizar/arquivar sem revisão humana. Nenhum teste ou aceite de preparação autoriza execução na Oracle.
