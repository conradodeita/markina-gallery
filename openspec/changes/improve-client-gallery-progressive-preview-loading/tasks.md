## 1. Portabilidade para a versão ativa

- [x] 1.1 Identificar o contrato no SHA ativo `aa7119c`: `/gallery/[galleryId]` redireciona para a coleção canônica; a grade autenticada fica em `/public-galleries/[galleryId]`. O componente já oferece `deferGridImages`, mas a rota canônica não o ativa.
- [x] 1.2 Cobrir carregamento tardio antes e depois da troca de pastas na rota canônica, mantendo capa, ampliação e padrão administrativo.
- [x] 1.3 Ativar a opção existente na rota canônica, sem substituir arquivos pela versão antiga do checkout local.

## 2. Validação da candidata

- [x] 2.1 Executar regressão antes/depois, testes frontend relevantes, lint, typecheck, build e OpenSpec nesta árvore baseada na produção.
- [x] 2.2 Revisar a diferença contra o SHA ativo e registrar a candidata e as limitações de publicação.

## Continuidade

A implementação inicial no checkout compartilhado foi validada com 62 testes focados, typecheck e build, mas sua base é anterior à unificação das rotas já publicada. Esses resultados não certificam esta árvore. O preparo autorizado agora ocorre no worktree `production-gallery-integration`, usando exclusivamente o SHA ativo e a ancestralidade de main. Não copiar as rotas do checkout antigo para esta branch.

O carregamento nativo distribui transferências de imagens conforme a viewport; não pagina metadados nem controla um número exato de requisições. A melhoria só poderá ser declarada publicada depois de aprovação/release do serviço web. Esta change permanece aberta para revisão humana, sem sincronização ou arquivo.


Regressão da candidata: antes da ativação, o teste de navegação de pastas falhou com `loading=null`; após a ativação, os 43 testes focados passaram. A opção é verificada na primeira pasta e na pasta exclusiva, e capa/ampliação/padrão do componente preservados. Build, typecheck e lint passaram (31 avisos, zero erros). A suíte completa inicial teve 512/513 passando com falha no ícone de login, arquivo sem diferença contra a produção; todos os 26 testes de login passaram isoladamente. A repetição completa com `npm test -- --maxWorkers=2` passou: 513/513 testes, 60/60 arquivos. O resultado inicial intermitente permanece registrado; não foi alterado código de autenticação.


Diff revisado contra `aa7119c`: apenas uma linha de código de produto (`deferGridImages` na coleção canônica) e dois arquivos de testes frontend. `backend/`, `docker/`, dependências e a rota legada continuam idênticos à versão ativa. A candidata está em `feature/production-gallery-integration`, baseada no merge local de produção com main; PR draft e aprovação de merge/release são os próximos gates. OpenSpec 1.14.0: 101/101 itens aprovados. Não há publicação remota do serviço nesta preparação.


Candidata publicada para revisão no PR draft https://github.com/conradodeita/markina-gallery/pull/179; correção no commit `6e32486ccbb960971b60ccc79029cf09deecabcc`. A integração permanece aguardando revisão/merge e posterior aprovação de release, sem alteração dos serviços no servidor.
