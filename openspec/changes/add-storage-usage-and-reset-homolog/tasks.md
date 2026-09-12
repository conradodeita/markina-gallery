## 1. Contratos inicialmente falhos

- [x] 1.1 Adicionar teste backend inicialmente falho para o resumo administrativo com bytes físicos somados nas três raízes, contagem de `PhotoAsset`, zero, erro de leitura isolado e negação sem sessão admin; verificar os ramos sem expor paths ou PII.
- [x] 1.2 Adicionar teste frontend inicialmente falho para o card `Armazenamento de fotos`, cobrindo zero, MB, GB, quantidade de fotos e estado indisponível sem bloquear as demais métricas.
- [x] 1.3 Estender as provas estruturais da manutenção com modo sem backup, trailer, flag e confirmação literal exclusivos; verificar que sinais incompletos não podem selecionar a execução destrutiva.

## 2. Métrica de armazenamento na Visão geral

- [x] 2.1 Implementar helper de medição das raízes `source`, `derivatives` e `history`, sem seguir symlinks, com soma de arquivos regulares, falha total segura e cache máximo de 30 segundos; verificar em diretórios temporários.
- [x] 2.2 Acrescentar `storage.photo_count`, `storage.bytes` e `storage.available` a `/admin/validation-summary`, usando `COUNT` e preservando autenticação/contrato agregado; verificar os testes backend focados.
- [x] 2.3 Implementar o card responsivo na Visão geral com formatação binária `0 MB`/MB/GB, pluralização de fotos e indisponibilidade local; verificar o teste de componente e ausência de regressão nas ações existentes.

## 3. Higienização sem backup em homologação

- [x] 3.1 Estender `maintain-homolog-data.sh` com inventário imediatamente anterior e modo `--without-backup` condicionado ao token `DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP`, preservando o modo padrão com dump; verificar a política estrutural e sintaxe shell.
- [x] 3.2 Estender o pipeline protegido com trailer exato distinto para a limpeza sem backup e passagem conjunta de modo, flag e confirmação; verificar que commits comuns continuam somente no inventário e que o trailer legado mantém backup.
- [x] 3.3 Validar a limpeza em PostgreSQL descartável com dados representativos, comprovando zero galerias, pastas, clientes, fotos e dependências, preservação de admin/sessão/fatores/preferências e ausência de acesso fora das raízes Markina.

## 4. Validação e operação autorizada

- [x] 4.1 Executar testes backend/frontend direcionados, política de deploy/manutenção, Ruff, ESLint, TypeScript, build, OpenSpec estrito e `git diff --check`; confirmar ausência de migration, segredo e alteração em preço, PIX, WhatsApp, mídia entregue ou reconhecimento facial.
- [ ] 4.2 Preparar e registrar inventário de impacto zero com SHA, projeto `markina-gallery`, `/opt/markina-gallery`, `127.0.0.1:8080`, subdomínio, contagens e bytes anteriores, sem PII; revisar o diff e publicar por commit, push e PR.
- [ ] 4.3 Após CI verde e merge autorizado, aprovar o Environment, executar o deploy e a limpeza sem backup novo pelo trailer exclusivo; verificar contagens operacionais e bytes zerados, admin/preferências preservados, serviços saudáveis, `FACIAL_PROCESSING_ENABLED=true` e Visão geral atualizada.
