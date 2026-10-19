# Tasks

## 1. Dependabot

- [x] 1.1 Limitar a um PR ordinário por cada uma das seis entradas, distribuir agendas pela semana e validar a estrutura YAML e os grupos por compatibilidade (YAML parseado com PyYAML; seis limites unitários; dias distintos).
- [x] 1.2 Confirmar que majors, dependências críticas e atualizações de segurança não sejam capturados por grupos ordinários (grupos aplicam-se somente a version-updates e só a patch/minor; referência: documentação oficial GitHub) e documentar o limite global resultante: seis PRs comuns; security updates têm limite separado do GitHub.

## 2. Classificação e CI

- [x] 2.1 Implementar classificador de caminhos com testes para frontend, backend, Gemma, imagens API/web e motores fotográficos, alterações globais e escopo desconhecido (10 testes unitários passaram).
- [ ] 2.2 Condicionar testes pesados ao escopo identificado, adicionar builds específicos das imagens API/web/fotográficas e preservar checks invariáveis; validar sintaxe do workflow e execução completa no GitHub Actions.
- [x] 2.3 Tornar `homolog-inventory-policy` agregador dos resultados e provar que falha do classificador, job necessário ausente, skipped ou failed bloqueia o check obrigatório (5 testes unitários do agregador passaram; as seis exigências de branch protection foram preservadas).

## 3. Integração e preparação dos candidatos

- [x] 3.1 Revalidar diffs, SHAs e checks dos PRs #232–#240; reutilizar os testes completos já concluídos para #236, #238 e #240 sem duplicá-los, conferir interações/arquivos/versões instaladas nos logs e registrar impacto somente em builds futuros (GitHub; base SHA `331296bce311b9918d8e6c61a086e6571a95ce42`).
- [ ] 3.2 Executar validação OpenSpec, testes do classificador, revisão do diff e CI completo da otimização; atualizar evidências e tarefas.
- [ ] 3.3 Abrir PR da automação, confirmar checks obrigatórios e estado das proteções; integrar somente se todos passarem, sem habilitar automerge ou tocar ambiente operacional.

## Workflow follow-up

- Sincronizar a spec principal e arquivar esta change somente após revisão humana, conforme o fluxo do repositório.
