# Tasks

## 1. Dependabot

- [x] 1.1 Limitar a um PR ordinário por cada uma das seis entradas, distribuir agendas pela semana e validar a estrutura YAML e os grupos por compatibilidade (YAML parseado com PyYAML; seis limites unitários; dias distintos).
- [x] 1.2 Confirmar que majors, dependências críticas e atualizações de segurança não sejam capturados por grupos ordinários (grupos aplicam-se somente a version-updates e só a patch/minor; referência: documentação oficial GitHub) e documentar o limite global resultante: seis PRs comuns; security updates têm limite separado do GitHub.

## 2. Classificação e CI

- [x] 2.1 Implementar classificador de caminhos com testes para frontend, backend, Gemma, imagens API/web e motores fotográficos, alterações globais e escopo desconhecido (10 testes unitários passaram).
- [x] 2.2 Condicionar testes pesados ao escopo identificado, adicionar builds específicos das imagens API/web/fotográficas e preservar checks invariáveis (CI `39302615704`: backend, frontend, Gemma, imagens, OpenSpec, Gitleaks e agregador passaram; testes de política atualizados para o novo gate de homologação).
- [x] 2.3 Tornar `homolog-inventory-policy` agregador dos resultados e provar que falha do classificador, job necessário ausente, skipped ou failed bloqueia o check obrigatório (5 testes unitários do agregador passaram; as seis exigências de branch protection foram preservadas).

## 3. Integração e preparação dos candidatos

- [x] 3.1 Revalidar diffs, SHAs e checks dos PRs #232–#240; reutilizar os testes completos já concluídos para #236, #238 e #240 sem duplicá-los, conferir interações/arquivos/versões instaladas nos logs e registrar impacto somente em builds futuros (GitHub; base SHA `331296bce311b9918d8e6c61a086e6571a95ce42`).
- [x] 3.2 Executar validação OpenSpec e regressões direcionadas, revisar o diff e concluir CI completo da otimização (OpenSpec 1.14.0 `validate --strict --all`: 125 itens; 24 testes de regressão; build das quatro imagens locais sem publicação; CI `39302615704` completo).
- [x] 3.3 Abrir a PR #241 e comprovar SHA, checks obrigatórios verdes, proteção estrita da `main`, ausência de aprovação requerida e escopo de release `none` (consultas GitHub e `classify_prod_release.py`).

## Workflow follow-up

- Integrar a PR #241 pela rota protegida depois de todos os checks passarem; não habilitar automerge.
- Sincronizar a spec principal e arquivar esta change somente após revisão humana, conforme o fluxo do repositório.
