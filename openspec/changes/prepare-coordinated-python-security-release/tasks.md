# Tasks

## 1. Inventário e contratos
- [x] 1.1 Coletar metadados Oracle, pacotes, imagens, filas agregadas e capacidade; registrar os oito consumidores e evidência sem dados pessoais. Evidência: validation.md e JSON sanitizados de 20/10.
- [x] 1.2 Delimitar leases, retries, inicialização e encerramento dos loops; documentar bloqueios comprovados antes de implementar gates. Evidência: design.md/validation.md e caminhos de código referenciados.

## 2. Candidatos isolados
- [x] 2.1 Implementar preparação restrita de quatro wheels por ID anterior, comparação completa de distribuições/base e reserva de espaço; testar rejeição de drift. Evidência: 29 testes novos e três candidatos reais com pip check zero.
- [ ] 2.2 Construir/verificar candidatos ARM64 viáveis e executar pip check, imports/contratos sintéticos; registrar bloqueios individuais de capacidade/homologação sem declarar resultados ausentes. PARCIAL/BLOQUEADO: API, worker, index e search SFace com candidatos verificados; quatro candidatos/homologações faltantes por capacidade, conforme tabela e recuperação documentadas em validation.md. Startup/import não comprova drenagem operacional.

## 3. Extensão oficial e simulação
- [x] 3.1 Estender entrada app para escopo Python sem fallback API/web; testar recusa operacional e nenhuma escrita diante de drenagem não implementada. Dispatch shell real e modos operacionais negativos passaram; pin exato e teste de adulteração preservados.
- [x] 3.2 Implementar/testar contrato sequencial simulado e rollback por ID nos oito cenários; documentar diferença entre simulação e executor operacional. Evidência: suíte nova de 29 testes, incluindo falha intermediária e dados legítimos preservados.
- [ ] 3.3 Completar executor operacional dos workers com drenagem cooperativa e rollback real verificável. BLOQUEADO: processos antigos não fornecem o contrato e a autorização não inclui alterar runtimes/loops para criá-lo. Não implementar stop baseado somente em contagem zero.

## 4. Integração e decisão
- [x] 4.1 Executar regressões, OpenSpec, revisão do diff e Code Review disponível; preparar PR focado com CI e gates preservados. Evidência: validation.md e PR #257. Conector externo sem conexão, explicitamente não verificado; revisão manual realizada. Checks obrigatórios permanecem exigidos na integração.
- [ ] 4.2 Integrar somente com checks/revisões aprovados e prova de ausência de deploy/preflight operacional; conferir CI pós-merge e registrar NO-GO se faltar executor/homologação.

## Workflow follow-up
- Não sincronizar/arquivar sem revisão humana. Publicação real depende de missão posterior e dos bloqueios registrados, não deste plano nem de fixtures.

## 5. Retomada limitada ao worker de prévias — 30/10/2026
- [x] 5.1 Revalidar consumidores ativos por metadados e identificar somente o worker de prévias como pendente dos quatro pins; preservar imagem anterior e excluir opcionais parados do plano.
- [x] 5.2 Preparar candidato ARM64 sobre a imagem exata, comparar todas as distribuições/camadas e validar pip check, HTTP sintético e JPEG/PNG com RawTherapee preservado. Evidência: candidato ef5105e0, 60 distribuições, somente quatro diferenças, hashes de render e binário idênticos em `preview-worker-preparation-20261030.md`.
- [x] 5.3 Gerar plano oficial local com o inventário real e registrar candidato, rollback e bloqueios operacionais em `preview-worker-preparation-20261030.md`. Resultado: somente prévias afetado; produção bloqueada por drenagem, homologação operacional e executor/recuperação ausentes.
- [x] 5.4 Validar os contratos existentes: 29 testes de preparação/política passaram; não ampliar o executor, não publicar e não reutilizar o release da migration 0090.

Esta retomada não completa automaticamente as tarefas históricas da primeira preparação coordenada nem autoriza atualizar consumidores já corrigidos ou parados.
