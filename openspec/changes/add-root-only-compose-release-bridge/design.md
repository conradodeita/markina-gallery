# Design

## Context

O preflight `44283691264` falhou antes de qualquer deploy. O proprietário escolheu a ponte root-only. A leitura read-only de 18/11/2026 confirmou fontes e diretórios diferentes de API/web e ausência do label `config-hash` em ambos. O proprietário autorizou explicitamente prova semântica por serviço. O recibo web compartilhado é anterior à imagem ativa e não comprova a identidade atual.

## Goals / Non-Goals

**Goals:** comprovar a configuração efetiva por serviço; preservar imagens, dependências faciais e rollback; manter CI, escopo, lock, aprovação e saída sem segredos.

**Non-Goals:** migrar para Compose canônico; alterar ambiente, schema, dados, workers ou recursos compartilhados; recriar containers para adicionar labels; expor configuração ou shell root.

## Decisions

- Helper de biblioteca padrão em `/usr/local/sbin/markina-gallery-app-compose-bridge`, `root:root 0755`. Dispatch explícito em `main`, Environment `production`, confere host, repositório, SHA/blob, backup, checksum e invariância dos containers. O forced-command wrapper continua pinado ao script app e só oferece inventários. Não modificar sudoers, chaves ou permissões existentes.
- O instalador aceita somente as URLs canônicas exatas `https://github.com/conradodeita/markina-gallery.git` e `ssh://github.com/conradodeita/markina-gallery.git`, que representam o mesmo repositório do produto. Não reescrever `remote.origin`; rejeitar host, caminho, protocolo ou credenciais diferentes antes de qualquer escrita privilegiada.
- Git, escopo e lock comum permanecem sob `ubuntu`. A ponte exige UID/GID root e tabela fechada de argumentos antes de qualquer consulta. Mutação exige modo apropriado, SHA/marcador correspondentes, lock ocupado e cópia root-only ligada ao fingerprint aprovado.
- Selecionar exatamente uma API e um web por labels. Arquivos e diretório são próprios de cada serviço. Aceitar somente checkout, estado protegido de origem e raiz privada da ponte; recusar symlink, hard link, escrita por terceiros, proprietário/hash divergentes. Fontes versionadas devem corresponder ao blob de `HEAD`.
- Resolver com cópias temporárias privadas das fontes e ambiente, mantendo `--project-directory` original e perfis fixos facial/preview. Remover cópias temporárias ao sair. Inventário não grava estado persistente nem altera imagens/containers. Nunca devolver stderr bruto, ambiente ou JSON Compose.
- Comparar snapshot resolvido com Docker inspect e defaults da imagem: ambiente sem duplicatas, comando/entrypoint, usuário/diretório, healthcheck, labels da aplicação, mounts, redes, restart, limites, privilégios, capabilities, segurança e portas. Campo sem contrato conhecido falha fechado. Digest semântico é distinto do label Compose; não sintetizar labels ausentes.
- Identidade web inicial exige prova do snapshot e revisão `io.pickyourpic.release` igual ao checkout ancestral aprovado. Não reescrever recibo antigo durante inventário. Após release, o novo recibo vincula imagem/digest semântico; recibos legados de hash Compose não substituem essa prova.
- Antes de build, preservar fontes byte a byte, modelos, metadados e fingerprint em `/var/lib/markina-gallery/app-compose-bridge/<operação>/` (`root:root 0700`, arquivos `0600`), fora do estado compartilhado gravável por ubuntu. Fontes originais permanecem intactas; nenhuma retenção/limpeza automática.
- API é construída sobre o ID imutável da imagem ativa, copiando somente `backend/app` obtido por `git archive` do SHA aprovado. Recusar qualquer mudança em requisitos, Dockerfile ou migrations. Isso conserva dependências/modelos faciais instalados. Web usa o contexto/Dockerfile versionados. Nunca usar contexto de build arbitrário extraído de snapshot.
- Publicação clona o modelo comprovado, fixa defaults da imagem antiga e altera somente imagem e `APP_VERSION` da API. Provar configuração prospectiva antes de trocar containers. Redes/volumes são externos; remover build/dependências do modelo aplicado. Executar por serviço com `--no-deps --no-build --pull never`.
- Rollback exige inventário/aprovação próprios, cópias e imagens verificadas do último release e preservação do runtime substituído. Restaurar somente API/web, sem banco ou segredos. Falha não dispara rollback automático. Nginx recebe apenas teste de configuração e reload já previstos.
- Confirmar imagens/versão, semântica, schema `20261113_0126`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, saúde e HTTPS antes de registrar sucesso. Falha conserva marcadores e recuperação.

## Risks / Trade-offs

Snapshots, defaults ou formatos sem contrato suportado bloqueiam; suporte adicional exige fixture e comparação efetiva. A fronteira root exige validação de argumentos, caminhos, modos, hash e negativas. API/web têm interrupção breve; builds/provas terminam antes e recuperação fica preservada. O estado privado cresce até existir política de retenção aprovada.

## Migration Plan

1. Fechar fixtures/prova, helper, integração, instalador, workflow e runbook; executar gates locais proporcionais ao risco.
2. Revisar diff/segredos, commit, push, CI/PR e merge verde.
3. Dispatch protegido instala ponte/wrapper e confere hash/metadados e invariância. Fetch somente dos objetos de main sem trocar checkout.
4. Preflight read-only confirma semântica, schema, facial, portas/domínio e fingerprint; divergência impede mutação.
5. Aprovação protegida e fingerprint idêntico permitem API/web; validar runtime, saúde/HTTPS e recuperação antes de marcar conclusão.

## Open Questions

Nenhuma decisão arquitetural pendente após a autorização da prova semântica. Gates operacionais ainda podem bloquear campos não comprovados; não relaxar contratos ou permissões automaticamente.
