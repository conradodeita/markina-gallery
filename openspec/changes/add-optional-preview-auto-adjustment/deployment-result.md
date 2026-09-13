# Resultado da publicação em homologação

## Integração e pipeline

- Commit funcional: `7075b2870e849a4dcdcb92a48cb1421360dacacb`.
- PR: `#81`, integrado em `develop` no merge `d2b52ca2e0f07e58b7075ee59d2467c5a435808e`.
- GitHub Actions: run `34773809694`; backend, frontend/build, OpenSpec, gitleaks e `deploy-homolog` aprovados.
- Deployment protegido `homolog`: `6424802756`.

## Verificação pós-deploy

- Checkout remoto limpo no SHA integral do merge.
- Alembic: `20260913_0054 (head)`.
- Configuração persistida: `enabled=false`, `generation=1`, `strength=50`.
- Fila exclusiva: zero registros; nenhuma foto foi agendada ou processada.
- Worker `preview-adjustment-worker`: ausente, conforme autorização e inventário.
- Nginx, web, API, worker comum e os três workers faciais da Markina: saudáveis.
- `/healthz` e `/api/health`: sucesso interno e externo em `https://markina-homolog.duckdns.org`.
- IDs dos containers Firefly, bancos persistentes, Nginx Proxy Manager e Portainer permaneceram iguais ao inventário anterior. Sem nova porta, alteração de proxy/DNS/certificado, down, prune, limpeza ou restore.

## Estado para avaliação

O painel e o backend estão publicados, mas o ajuste não está operacionalmente ativo. Para a avaliação estética, ainda será necessário obter autorização própria para provisionar/iniciar somente o worker opcional, habilitar a chave pelo painel e processar uma amostra real escolhida pelo fotógrafo. Isso não faz parte deste deploy e a task 4.2 permanece pendente.
