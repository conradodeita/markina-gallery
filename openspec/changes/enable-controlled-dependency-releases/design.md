# Design

## Context

Ver proposal.md. A main inicial é 48e877846f1b9f4f4f9c9cd7bdda7a545e9984a2. O classificador omite manifests; o executor app está pinado no wrapper do servidor e cobre somente api/web. Não alterar esse pin nem o host nesta missão. O SSH padrão foi recusado; em seguida o proprietário indicou a identidade SSH existente e a coleta somente leitura passou (validation.md).

## Goals / Non-Goals

Preparar análise reproduzível e permitir o caminho web-only existente com isolamento comprovado. Não criar executor genérico para workers, afrouxar blobs/gates app ou atualizar o wrapper Oracle. A lacuna de publicação/rollback de workers permanece bloqueio explícito permitido pelo pedido.

## Decisions

1. Um módulo Python sem novas dependências lê os manifests Compose versionados e os Dockerfiles, deriva os includes de requisitos e relata consumidores por imagem/serviço. Formas não reconhecidas falham fechadas. Classe `dependencies` nunca satisfaz `app`/`facial` no workflow existente; infraestrutura sozinha continua `none`.
2. Web-only valida o contexto Compose resolvido exatamente em `/opt/markina-gallery/frontend`, sem contextos/args/secrets adicionais, Dockerfile/.dockerignore aprovados e árvore Git sem symlinks/submódulos. Compara backend admitindo somente manifests conhecidos; código, migrations, Compose e alterações do build web permanecem protegidos. Registra hash da árvore frontend como proveniência de entrada, explicitamente distinto de digest de imagem.
3. O SHA/ID observado da API e snapshot não-web permanecem preservados quando o checkout passa ao SHA misto. Nenhum marcador de API é atualizado para o SHA web. A checagem da API contra checkout aceita apenas manifests pendentes, mantendo a recusa para código divergente.
4. Plano offline requer inventário sanitizado real; ausência nunca é preenchida por fixture. API e workers são relatados; o executor API/web existente não cobre workers. O plano Python bloqueia esses consumidores em vez de publicá-los ou ampliar o executor pinado.
5. Coletor sem argumentos mutáveis é enviado via stdin ao Python pelo SSH existente autorizado. Lê somente labels/estado/imagens/portas/recibos e metadados dos pacotes selecionados, sem abrir chave ou mapa de ambiente. Não adicionar workflow nem alterar o wrapper: o canal existente fornecido pelo proprietário já atende a coleta. Não fazer fetch no host.

## Risks / Trade-offs

- Parser restrito → rejeitar construções desconhecidas e testar os manifests reais, sem tratar análise como validação Compose completa.
- Contexto web pode conter arquivos ignorados → recusar entradas não versionadas que não sejam excluídas pelas regras aprovadas; ignorar apenas caches/pastas já excluídos do Docker context. Não consultar conteúdo de .env.
- Workers especializados compartilham os requisitos → manter homologação e executor/rollback próprios como bloqueios, sem ativar opcionais.
- Ausência de acesso/artefatos → registrar lacuna; não produzir digests ou versões fictícias.

## Migration Plan

PR de infraestrutura com CI, testes de gates e revisão; merge só com jobs de produção comprovadamente não acionados. Após merge, repetir somente a coleta de metadados pelo SSH existente. Release e rollback reais exigem execução posterior autorizada; sem migrations. Não sincronizar/arquivar specs nesta missão.
