## 1. Portabilidade para a versão ativa

- [x] 1.1 Identificar o contrato no SHA ativo `aa7119c`: `/gallery/[galleryId]` redireciona para a coleção canônica; a grade autenticada fica em `/public-galleries/[galleryId]`. O componente já oferece `deferGridImages`, mas a rota canônica não o ativa.
- [ ] 1.2 Cobrir carregamento tardio antes e depois da troca de pastas na rota canônica, mantendo capa, ampliação e padrão administrativo.
- [ ] 1.3 Ativar a opção existente na rota canônica, sem substituir arquivos pela versão antiga do checkout local.

## 2. Validação da candidata

- [ ] 2.1 Executar regressão antes/depois, testes frontend relevantes, lint, typecheck, build e OpenSpec nesta árvore baseada na produção.
- [ ] 2.2 Revisar a diferença contra o SHA ativo e registrar a candidata e as limitações de publicação.

## Continuidade

A implementação inicial no checkout compartilhado foi validada com 62 testes focados, typecheck e build, mas sua base é anterior à unificação das rotas já publicada. Esses resultados não certificam esta árvore. O preparo autorizado agora ocorre no worktree `production-gallery-integration`, usando exclusivamente o SHA ativo e a ancestralidade de main. Não copiar as rotas do checkout antigo para esta branch.

O carregamento nativo distribui transferências de imagens conforme a viewport; não pagina metadados nem controla um número exato de requisições. A melhoria só poderá ser declarada publicada depois de aprovação/release do serviço web. Esta change permanece aberta para revisão humana, sem sincronização ou arquivo.
