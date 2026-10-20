# Tasks

## 1. Inventário e contratos
- [x] 1.1 Coletar metadados Oracle, pacotes, imagens, filas agregadas e capacidade; registrar os oito consumidores e evidência sem dados pessoais. Evidência: validation.md e JSON sanitizados de 20/10.
- [x] 1.2 Delimitar leases, retries, inicialização e encerramento dos loops; documentar bloqueios comprovados antes de implementar gates. Evidência: design.md/validation.md e caminhos de código referenciados.

## 2. Candidatos isolados
- [ ] 2.1 Implementar preparação restrita de quatro wheels por ID anterior, comparação completa de distribuições/base e reserva de espaço; testar rejeição de drift.
- [ ] 2.2 Construir/verificar candidatos ARM64 viáveis e executar pip check, imports/contratos sintéticos; registrar bloqueios individuais de capacidade/homologação sem declarar resultados ausentes.

## 3. Extensão oficial e simulação
- [ ] 3.1 Estender entrada app para escopo Python sem fallback API/web; testar recusa operacional e nenhuma escrita diante de drenagem não implementada.
- [ ] 3.2 Implementar/testar contrato sequencial simulado e rollback por ID nos oito cenários; documentar diferença entre simulação e executor operacional.
- [ ] 3.3 Completar executor operacional dos workers com drenagem cooperativa e rollback real verificável. BLOQUEADO: processos antigos não fornecem o contrato e a autorização não inclui alterar runtimes/loops para criá-lo. Não implementar stop baseado somente em contagem zero.

## 4. Integração e decisão
- [ ] 4.1 Executar regressões, OpenSpec, revisão do diff e Code Review disponível; preparar PR focado com CI e gates preservados.
- [ ] 4.2 Integrar somente com checks/revisões aprovados e prova de ausência de deploy/preflight operacional; conferir CI pós-merge e registrar NO-GO se faltar executor/homologação.

## Workflow follow-up
- Não sincronizar/arquivar sem revisão humana. Publicação real depende de missão posterior e dos bloqueios registrados, não deste plano nem de fixtures.
