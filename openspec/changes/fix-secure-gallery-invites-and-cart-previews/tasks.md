# Tasks

## 1. Origem segura dos convites

- [ ] 1.1 Extrair a validação da origem pública para uso compartilhado, preservando precedência de `PUBLIC_APP_ORIGIN`, compatibilidade de notificações e HTTP local; verificar testes focados de origens válidas/inválidas, novo domínio e notificações existentes, registrando resultados em `validation.md`.
- [ ] 1.2 Aplicar a origem validada a todos os links de capacidade retornados pela API administrativa e validar antes de emissões/rotações persistentes; verificar com testes de criação, leitura, convite individual e rotação que cabeçalhos host/proto divergentes não mudam o HTTPS, e que origem insegura não devolve token nem persiste capacidade nova. Registrar os endpoints cobertos em `validation.md`.

## 2. Prévia protegida no carrinho

- [ ] 2.1 Admitir somente a rota operacional protegida da galeria canônica no resolvedor compartilhado de prévias; verificar testes de renderização no carrinho, prefixo `/api` único, compatibilidade de rotas antigas e rejeição de URL externa, original, admin, travessia, query/fragmento e mídia ausente. Registrar a evidência em `validation.md`.
- [ ] 2.2 Verificar no backend que a rota canônica exige sessão, vínculo e público da pasta para uma foto selecionada; executar teste focado de cliente autorizada, outra cliente e pasta restrita, sem alteração de autorização, e registrar resultado em `validation.md`.

## 3. Integração e publicação controlada

- [ ] 3.1 Executar testes focados cruzados, lint/typecheck/build aplicáveis, validação OpenSpec estrita e revisão do diff/segredos; registrar comandos, resultados e limitações em `validation.md`, incluindo que não houve migration nem edição de configuração persistida.
- [ ] 3.2 Preparar commit/PR restrito à change, sem publicar em `develop`; verificar SHA, arquivos e CI acionada pelo PR, então parar enquanto o proprietário informa o resultado da CI.
- [ ] 3.3 Após CI verde e aprovação operacional específica, inventariar SHA/schema, porta/subdomínio e vizinhos, apresentar impacto zero/backup/reversão e só então integrar/deployar; verificar HTTPS do convite e prévia no carrinho com dados sintéticos autorizados, limpar o ensaio e registrar saúde/admin/Evolution sem pagamento real. Se a autorização ou participação humana faltar, registrar o bloqueio e manter a task aberta.
- [ ] 3.4 Após revisão humana do resultado completo, sincronizar as specs principais e arquivar esta change; verificar validação OpenSpec e registrar a aprovação, sem marcar aceite remoto ou arquivo por CI isoladamente.
