# Design

## Context

O release app é executado somente em push a `main`. O inventário disponível identificou o runtime `b4f15abd6a71585082758062feba7fcfcc225587`, Alembic `20261017_0084`, domínio `https://markina.pickyourpic.com.br` e Nginx Markina em `127.0.0.1:8080`; `main` está na ancestral `b695b2e` e `develop` está no runtime inventariado. A PR #220 adiciona apenas a identificação dos responsáveis, sem migration, e está validada contra `develop`.

## Goals / Non-Goals

**Goals:**

- Fazer a classificação de release usar um SHA saudável de produção registrado, para separar a reconciliação do histórico já publicado do delta novo.
- Permitir o delta exato de identificação de responsáveis pelo gate API/web com blobs versionados e schema `20261017_0084`.
- Preservar preflight somente-leitura, fingerprint, aprovação protegida e release/rollback limitados a `api` e `web`.

**Non-Goals:**

- Publicar o código de `develop` como um todo, executar migrations ou alterar a linha do worker OTP.
- Recriar workers faciais, banco, Redis, Nginx, Compose, volumes, proxy compartilhado ou serviços de terceiros.
- Instalar remotamente o wrapper root-owned ou executar publicação antes de novo inventário e aprovação operacional específicos.

## Decisions

- O manifesto do release guardará o SHA saudável de produção e a revisão Alembic observados. O classificador somente examinará commits descendentes desse SHA; um alvo que ainda não descende dele (ou que apenas reconcilia o histórico até ele) não selecionará release. O avanço do baseline após publicação saudável será registrado como atualização operacional sem delta de runtime.
- O manifesto de blobs incluirá somente `backend/app/main.py`, o módulo `backend/app/private_folder_overview.py`, o componente `frontend/app/admin/galleries/private-folder-client-overview.tsx` e o editor `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx`. Testes, OpenSpec e runbooks podem acompanhar; outros runtimes continuam fora do escopo.
- O preflight API/web exigirá revisão `20261017_0084` e ausência de migrations entre o checkout ativo e o candidato. O script de release não executará Alembic e usará `--no-deps` para `api web`.
- O wrapper SSH versionado aceitará somente o novo comando de inventário read-only e o comando API/web já restrito, ambos com SHA completo e scripts fixados por blob. A cópia root-owned do servidor permanece um pré-requisito operacional separado e deve ser instalada/conferida pelo procedimento documentado.
- A PR #220 será reconciliada com `main`, preservando como ancestral o SHA já implantado. O classificador exportará esse baseline ao gate app: a diferença histórica entre branches não pode virar delta de publicação. A integração reúne o recurso e seus controles na mesma PR, evitando integrações intermediárias sem mudança no servidor. O workflow de homologação amplo não será usado.

## Risks / Trade-offs

- [A revisão 0084 ou o SHA ativo mudaram desde o inventário anterior] → o preflight atualiza os valores observados e o candidato falha fechado até que manifesto, ancestralidade e teste sejam reconciliados.
- [O classificador poderia incluir código histórico em uma reconciliação de linha] → comparar com baseline explícito, exigir ancestralidade e testar que a reconciliação gera `none` e que um delta app descendente gera `app`.
- [A atualização root-owned do wrapper ainda não foi feita] → registrar como bloqueio operacional; não contornar por SSH arbitrário nem disparar `deploy-homolog`.
- [Recriar API/web provoca breve indisponibilidade] → apresentar no inventário, preservar imagens anteriores e habilitar rollback separado, sujeito a novo fingerprint e aprovação.
- [O cliente OTP pode depender de API/web] → o OTP pode sofrer a mesma breve interrupção da API durante o restart, mas seu worker não será recriado; confirmar saúde do worker antes e depois do release.

## Migration Plan

1. Implementar e testar os manifests, classificador, gates, wrapper versionado e runbook sem acessar serviços mutáveis.
2. Integrar localmente o gate à PR #220, preservando o histórico de `main`, `develop` e o commit original do recurso, sem force-push.
3. Confirmar que a classificação usa o SHA instalado e que o diff desde esse SHA contém apenas os runtimes app e controles declarados; uma reconciliação sem novo runtime continua retornando `none`.
4. Retargetar a PR #220 para `main`, executar CI completo e verificar classificação `app`, blobs e ausência de migrations no delta de publicação.
5. Atualizar/conferir a cópia root-owned do wrapper conforme o procedimento do servidor. Executar preflight read-only no SHA candidato e apresentar ao proprietário SHA atual/alvo, schema, serviços, portas, domínio, fingerprint, impacto e rollback.
6. Após aprovação específica do inventário/fingerprint e do Environment `production`, recriar somente `api` e `web`; confirmar SHA, schema invariável, smoke tests e estado do worker OTP.
7. Se houver falha, não executar rollback automático. Preparar inventário de rollback limitado a API/web e aguardar autorização específica.

