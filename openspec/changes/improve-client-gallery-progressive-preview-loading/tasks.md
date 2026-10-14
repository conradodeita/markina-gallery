## 1. Portabilidade para a versão ativa

- [x] 1.1 Identificar o contrato no SHA ativo `aa7119c`: `/gallery/[galleryId]` redireciona para a coleção canônica; a grade autenticada fica em `/public-galleries/[galleryId]`. O componente já oferece `deferGridImages`, mas a rota canônica não o ativa.
- [x] 1.2 Cobrir carregamento tardio antes e depois da troca de pastas na rota canônica, mantendo capa, ampliação e padrão administrativo.
- [x] 1.3 Ativar a opção existente na rota canônica, sem substituir arquivos pela versão antiga do checkout local.

## 2. Validação da candidata

- [x] 2.1 Executar regressão antes/depois, testes frontend relevantes, lint, typecheck, build e OpenSpec nesta árvore baseada na produção.
- [x] 2.2 Revisar a diferença contra o SHA ativo e registrar a candidata e as limitações de publicação.
- [x] 2.3 Integrar a candidata e publicar somente o serviço web após aprovação explícita; confirmar saúde do container e endpoints HTTPS.

## Continuidade

A implementação inicial no checkout compartilhado foi validada com 62 testes focados, typecheck e build, mas sua base é anterior à unificação das rotas já publicada. Esses resultados não certificam esta árvore. O preparo autorizado agora ocorre no worktree `production-gallery-integration`, usando exclusivamente o SHA ativo e a ancestralidade de main. Não copiar as rotas do checkout antigo para esta branch.

O carregamento nativo distribui transferências de imagens conforme a viewport; não pagina metadados nem controla um número exato de requisições. A change permanece aberta para revisão humana; sincronização às specs principais e arquivo ainda não foram feitos.


Regressão da candidata: antes da ativação, o teste de navegação de pastas falhou com `loading=null`; após a ativação, os 43 testes focados passaram. A opção é verificada na primeira pasta e na pasta exclusiva, e capa/ampliação/padrão do componente preservados. Build, typecheck e lint passaram (31 avisos, zero erros). A suíte completa inicial teve 512/513 passando com falha no ícone de login, arquivo sem diferença contra a produção; todos os 26 testes de login passaram isoladamente. A repetição completa com `npm test -- --maxWorkers=2` passou: 513/513 testes, 60/60 arquivos. O resultado inicial intermitente permanece registrado; não foi alterado código de autenticação.


Diff revisado contra `aa7119c`: apenas uma linha de código de produto (`deferGridImages` na coleção canônica) e dois arquivos de testes frontend. `backend/`, `docker/`, dependências e a rota legada continuam idênticos à versão ativa. OpenSpec 1.14.0: 101/101 itens aprovados. O PR #179 foi integrado em `main` no commit `69965dfd7ef3bb336eebe202ea6a21adebc0a0e5` após CI verde. A validação completa local incluiu suíte frontend 513/513, TypeScript, lint (31 avisos, zero erros), build e validações dos scripts de operação.


Publicação de produção em 2026-10-14 no host `clearbudget-vnic`, domínio `markina.pickyourpic.com.br`: o inventário confirmou o checkout limpo, o hash de configuração web esperado, Nginx publicado apenas em `127.0.0.1:8080` e todos os serviços Markina saudáveis antes da operação. O script `scripts/deploy-prod-web.sh` construiu e recriou somente `web` para o commit `69965dfd7ef3bb336eebe202ea6a21adebc0a0e5`; nenhuma alteração foi feita em API, banco, Redis, workers, Nginx, arquivos de ambiente ou recursos compartilhados. Pós-publicação: `web-last-healthy.sha` corresponde ao commit integrado, o container web está healthy, API e demais containers permanecem healthy, `/healthz`, `/api/health` e `/` responderam HTTP 200. O SHA anterior `aa7119c0b82bd5fa147fe6bbdac98dfa21091190` está preservado em `web-previous.sha` para rollback. PR #179: https://github.com/conradodeita/markina-gallery/pull/179. A change segue aberta para revisão humana; não sincronizar nem arquivar ainda.
