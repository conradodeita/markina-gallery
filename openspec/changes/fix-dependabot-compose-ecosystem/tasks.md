# Tasks

## 1. Corrigir e proteger a configuração

- [x] 1.1 Trocar somente o ecossistema de `/docker` para `docker-compose`; preservar Docker backend/frontend, limite, agenda, grupos e ausência de automerge.
- [x] 1.2 Adicionar regressão que assegure a entrada correta e a cobertura dos cinco manifests Compose base/overlays encontrados no repositório.
- [x] 1.3 Executar os testes direcionados, validar o OpenSpec e rever o diff para confirmar ausência de mudanças em versões, imagens, serviços ou deploy (9 testes do relatório passaram; `openspec validate fix-dependabot-compose-ecosystem --strict` passou; `git diff --check` passou; diff limitado à configuração, teste e artifacts OpenSpec).

## 2. Validar e integrar

- [ ] 2.1 Abrir PR para `main`, validar a configuração Dependabot no GitHub e acompanhar todos os checks obrigatórios.
- [ ] 2.2 Verificar a execução Dependabot disparada pela nova configuração quando disponível; não integrar PRs Dependabot que ela criar.
- [ ] 2.3 Integrar somente após checks verdes e confirmar que jobs de deploy/Oracle não foram acionados.
