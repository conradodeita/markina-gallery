# Tasks: Entrega protegida do segredo OAuth do Google Drive

- [x] 1.1 Implementar leitura estrita do JSON OAuth Web no caminho dedicado, com checagem de arquivo regular, modo `0400`, sem symlink, URI de produção exata e falha sem fallback para ambiente. Evidência no diff de `backend/app/google_drive_oauth.py`.
- [x] 1.2 Adaptar os testes existentes de configuração OAuth para arquivo sintético; validar arquivo ausente, permissões, symlink, JSON/cliente/URI inválidos, URI múltipla e ausência de fallback. Evidência: suíte OAuth completa 34 passed na primeira rodada; após o endurecimento final, oito casos focados passaram em imagem isolada sem rede; sem conta Google.
- [ ] 1.3 Fechar lint, OpenSpec, diff e build sem atualizar dependências; publicar branch para CI e validar a camada sobre a imagem API exata em produção. Evidência local parcial: Ruff, compileall, OpenSpec strict e diff-check passaram; o build padrão resolveu dependências `>=` mais novas e foi descartado como candidato de produção. Construir overlay sobre o digest em produção.
- [ ] 1.4 Fazer deploy blue/green somente da API, montar o arquivo host read-only, remover variáveis `GOOGLE_DRIVE_*` de `.Config.Env` e confirmar saúde, TOTP, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true` e três endpoints públicos. Preservar a API anterior sem segredo Drive como rollback.
- [ ] 1.5 Registrar o resultado operacional; confirmar que consentimento, uploads, backups e dados de clientes permaneceram intocados.

## Checkpoint local — 17/11/2026

O build padrão de validação instalou dependências mais novas por constraints abertas; não será promovido. A imagem candidata de produção será uma camada baseada no digest API ativo, contendo apenas o módulo OAuth atualizado e o teste correspondente. O build overlay no host e a CI da branch ainda estão pendentes.
