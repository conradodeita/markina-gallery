# Design

## Contexto

O Dependabot contém seis entradas: npm em `/frontend`, pip em `/backend`, três diretórios Docker e GitHub Actions na raiz. O limite atual é quatro PRs por entrada (até 24 ordinários), todos agendados na segunda-feira. O CI atual executa backend, frontend e build/inferência Gemma em cada PR. A proteção da `main` exige `backend`, `frontend`, `gemma-runtime`, `openspec`, `homolog-inventory-policy` e `gitleaks`.

## Decisões

- Definir `open-pull-requests-limit: 1` em cada entrada. O teto ordinário configurado passa a seis PRs, sem remover entradas ou cadência de segurança.
- Agendar npm terça, pip quarta, Docker backend quinta, Docker frontend sexta, Docker Compose sábado e Actions segunda, sempre às 10:00 de São Paulo.
- Agrupar npm somente em famílias Next/React e testes/ferramentas, patch/minor. Em pip, agrupar patch/minor somente nas famílias Web Push, face (NumPy/OpenCV) e Gemma (Transformers/Hub/Sentence Transformers/Torch/Torchvision). Atualizações de bancos, autenticação e majors ficam individuais. Docker e GitHub Actions não agrupam componentes distintos.
- Implementar classificador Python stdlib que lê caminhos alterados e emite flags no formato `GITHUB_OUTPUT`. Pull requests usam comparação entre SHA base e head; push e execução manual executam todas as validações.
- Backend roda para mudanças em `backend/**`; frontend para `frontend/**`; Gemma roda para código/requirements/modelos faciais e Gemma. Mudanças nos workflows ou no próprio classificador executam todos os escopos. Atualizações de manifestos/Dockerfiles selecionam builds locais das imagens de API, web, prévia e RAW afetadas, sem publicar ou iniciar serviços.
- Os cinco jobs de validação permanecem com os mesmos nomes exigidos. `homolog-inventory-policy`, também obrigatório, aguarda todos com `always()` e confirma que cada escopo marcado executou com sucesso; falha do classificador, job requerido ausente ou qualquer job com falha torna o agregador vermelho. OpenSpec, Gitleaks e políticas existentes permanecem incondicionais.
- Jobs de build fotográfico são condicionais e não necessários quando seus arquivos não mudaram; quando necessários, são incluídos no mesmo agregador obrigatório.

## Segurança e operação

- Sem `paths` no gatilho do workflow: o check continua sendo criado para todo PR e não desaparece por filtro de trigger.
- Nenhuma permissão nova de escrita, segredo, credencial, checkout de repositório externo ou serviço real será introduzida.
- `workflow_dispatch` e pushes em `develop`/`main` mantêm validação completa, inclusive antes de quaisquer jobs já existentes de deploy protegidos.
- Os grupos Dependabot aplicam-se somente a `version-updates`; alertas e security updates permanecem no mecanismo nativo, fora do limite de PRs ordinários.

## Questões em aberto

Nenhuma. A consulta do GitHub confirmou que Dependabot alerts e security updates estão desabilitados e não podem ser habilitados pela configuração versionada; o proprietário deverá ativá-los nas configurações de segurança do repositório.
