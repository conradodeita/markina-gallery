# Design

## Context

Produção observada em fe1f3bc6, imagem web sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573, vinculada ao log de release app. Marcador web d9c8 está obsoleto. A correção de dependências está em main 81eb0741 e fora de produção.

## Goals / Non-Goals

Corrigir o protocolo e testá-lo fora de produção. Não publicar, reiniciar, migrar, limpar, mudar produto, instalar wrapper ou editar estado remoto nesta fase.

## Decisions

- Um recibo `web-current.identity` contém quatro campos separados por espaço: SHA de origem, ID completo sha256 Docker, hash Compose e checkout conhecido. `web-previous.identity` e `web-pending.identity` preservam recuperação; validação estrita recusa formatos/symlinks e imagens ausentes. A escrita de recibos é atômica no diretório de estado. Tags de recuperação usam ID da imagem e sua identidade é conferida; conflito não é sobrescrito.
- Web e app validam o recibo contra a imagem efetivamente usada, nunca escolhem versão só pela precedência de marcadores. O app confirma que o backend da versão API é idêntico ao checkout quando houve web-only intermediário; guarda a identidade web e a versão API anterior no rollback. Depois de app saudável, publica novo recibo web; depois de rollback restaura o recibo salvo.
- Adoção legada é operação separada `reconcile-inventory`/`reconcile`, com SHA/ID explícitos, fingerprint, runtime saudável e origem comprovada pelo operador nos logs. Só cria recibo ausente; não corrige conflito automaticamente. Não copia marcadores históricos.
- Objetos Git do alvo devem existir localmente. Inventários desabilitam optional locks/lazy fetch, não usam mktemp/fetch/flock e fazem apenas consultas. São snapshots; release/rollback/reconcile abrem lock existente para leitura, adquirem flock exclusivo e repetem toda validação antes de escrever. In-flight app/web/rollback impede cruzamento de fluxos.
- Código de suporte é obtido do objeto Git do SHA explicitamente selecionado, após validar raiz/origin/main. Isso permite execução do script imutável por stdin sem depender de uma cópia auxiliar antiga no checkout. Em rollback usa suporte da main aprovada, não do commit histórico restaurado. Os pins do wrapper e dos dois helpers permanecem exatos; carregamento usa pipes, sem here-string grande que possa criar temporário.
- Web compara backend, Compose e Dockerfile do alvo antes de trocar checkout. Fingerprint inclui recibos, imagem de recuperação e estado dos outros serviços; imagem, saúde e configuração são verificadas novamente após build. Runtime não-web deve manter IDs/imagens/início/configuração, sem escrita nesses serviços.
- Antes do build, preserva ID atual e grava pending com checkout original. Build falho não recria web; deixa recuperação explícita possível. Depois do build, revalida runtime; somente web é recriado com no-deps/no-build. Saúde exige ID esperado, hash Compose, HTTPS e Estatísticas 404. Não realiza rollback automático: uma operação contingencial aprovada executa `recover-inventory`/`recover` pelo recibo pending, inclusive quando web estiver ausente ou unhealthy. O ID construído é persistido antes da troca; recuperação recusa imagem corrente fora do par anterior/construída. Rollback de release concluído aceita unhealthy com identidade atual comprovada. Erro em recuperação conserva pending e bloqueia novo release; nunca limpa evidência de falha para declarar sucesso.
- O fluxo app mantém seu escopo API/web, schema, allowlist, aprovação protegida e recarga nginx já especificados. Não será usado para esta publicação. Suas falhas mantêm os registros duráveis para rollback aprovado; nenhuma ampliação de serviços.

## Risks / Trade-offs

Sem recibo, publicação falha fechada até adoção autorizada; origem legada não pode ser deduzida só de Docker. Tags não são imutáveis, IDs são; conferir ambos. Snapshot sem lock pode envelhecer e exige revalidação sob lock. O nginx versionado já usa resolver Docker válido por 10 s e proxy web por variável; verificar esse contrato e HTTPS sem recarregar nginx, ou recuperar/abortar se HTTP falhar. Breve interrupção web possível; nenhuma promessa de zero downtime.

## Migration Plan

Engenharia e CI isolados; PR e merge com release_scope=none. Preparar runbook no SHA final. Após única autorização futura: obter alvo sem trocar aplicação, validar runtime e evidências, adotar recibo, preservar imagem, inventário/fingerprint e release somente web. Recuperação restaura ID/checkout anterior e valida saúde. Não atualizar wrapper remoto nem executar fluxo app nesta operação.

## Open Questions

Nenhuma decisão de produto. A execução Oracle continua proibida até autorização operacional específica.
