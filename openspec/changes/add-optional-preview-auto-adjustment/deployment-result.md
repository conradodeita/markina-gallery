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

## Provisionamento do worker — autorização posterior

Em 13/09/2026, após esclarecer o controle administrativo e a persistência do serviço, o proprietário autorizou iniciar o worker para seus primeiros testes. Inventário atualizado: mesmo SHA, serviços existentes saudáveis, 33% de disco usado, 132 GiB livres e aproximadamente 21 GiB de memória disponíveis. Plano apresentado: adicionar somente preview-adjustment-worker, sem portas, com 0,5 CPU/768 MiB e restart unless-stopped, usando o ambiente seguro existente. A chave do módulo fica sob controle do admin no painel.

Build/start concluídos com --no-deps. Imagem ARM `sha256:21a51aa371e790c03f6bc6b8c3cb14ec96ec1d1eb439cbbc2b9c2a8311ab06e4`, container `3b2d57d791ac`, health healthy. Limites e restart conferidos no Docker; banco acessível, configuração ainda false, zero jobs. RawTherapee renderizou entrada sintética de 640×420 em 0,640 s, preservando entrada/dimensões. Isso verifica execução, não qualidade estética nem capacidade de lote. Healthchecks externos aprovados e IDs de todos os containers anteriores preservados.

O admin já pode marcar Melhorar prévias automaticamente em Configurações e salvar. Para fotos existentes, selecionar a galeria e Processar galeria / tentar falhas. A avaliação estética 4.2 permanece humana. Em futuras publicações que alterem o pacote preview_adjustment, atualizar também este worker usando o override; o pipeline base não o reconstrói automaticamente.
