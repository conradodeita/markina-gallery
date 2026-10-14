# Tasks

## 1. Corrigir a origem usada pelo inventário

- [x] 1.1 Atualizar o workflow para receber e validar `HOMOLOG_PUBLIC_BASE_URL` do Environment `homolog`; confirmar por teste de política que URL ausente/inválida aborta antes da conexão SSH e dos probes.
- [x] 1.2 Atualizar o script remoto para receber a origem esperada, compará-la ao `PUBLIC_APP_ORIGIN` do Compose e emitir somente hostname; validar que divergência aborta antes de `compose ps` e do container transitório.
- [x] 1.3 Reutilizar a origem validada para `/healthz` e `/api/health`; proteger por teste que workflow e script não contêm hostname fixo antigo.

## 2. Validar e registrar a correção

- [x] 2.1 Executar teste de política do inventário, `bash -n` e validação OpenSpec strict; registrar comandos e resultados em `validation.md`.
- [ ] 2.2 Após a revisão e integração da correção em `main`, executar o workflow read-only com o SHA real de homologação e verificar hostname, health checks, isolamento do projeto e ausência de mutações.
