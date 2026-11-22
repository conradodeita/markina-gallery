# Reconciliação do preflight API/web — 18/11/2026

## Escopo e baseline observados

- O proprietário autorizou prosseguir pelos gates, merge e deploy sem nova intervenção. O deploy aprovado continua limitado a `api` e `web`, sem migration ou mudança de dados/configuração facial.
- Host `clearbudget-vnic`, projeto `markina-gallery`, checkout publicado observado `bfe511f850224823254b0fc9f51fa7ff60ecfba0`; `APP_VERSION` coincide com esse SHA. O candidato integrado após PR #376 é `6d92ec203599f9cad35777e640186461b63d6da7`.
- Ambiente e estado previamente observados no host: `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, schema `20261113_0126`, ingresso Markina em `127.0.0.1:8080` e `https://markina.pickyourpic.com.br`. Estes valores precisam ser revalidados pelo preflight mais recente antes do release.
- Nenhuma migration, alteração de `.env`, dados de tenant, segredo, container, imagem, volume, worker ativo, proxy ou porta faz parte do deploy.

## Gates já concluídos

- PR #376 `fix(deploy): remove retired RAW overlay from app inventory` foi integrada em `main` no commit `6d92ec203599f9cad35777e640186461b63d6da7`; CI da PR `44236805663` passou.
- O workflow `44243882449`, attempt 1, atualizou o wrapper root-owned. O wrapper atual é `root:root`, modo `0755`, SHA-256 `846c4519d9dd822086cf190939acb55f87040e950d68489def923e89269eb152`. O backup anterior foi preservado e verificado pelo workflow.
- A preparação Git remota buscou somente os objetos/ref de `origin/main`, sem trocar o checkout ativo. O checkout remoto continuou em `bfe511f850224823254b0fc9f51fa7ff60ecfba0` e permaneceu limpo.
- No workflow `44247817045`, attempt 1 não havia objeto remoto do candidato; após a preparação, attempt 2 passou os gates de código e falhou no inventário Compose. O release foi ignorado; não houve mutação de aplicação.

## Diagnóstico do Compose

- O erro exato do preflight foi `service "face-gemma-index-worker" has neither an image nor a build context specified: invalid compose project`.
- A declaração não está nos manifestos versionados. Ela aparece no overlay persistente `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`, pertencente a `ubuntu:ubuntu`, modo `0600`, tamanho 653 bytes, SHA-256 `c63599b84764f6141cf9860ce1a352f6e11eae55ea4c24b75959ca277c3cd60e`.
- A inspeção estrutural não exibiu valores e confirmou que esse bloco contém somente `environment.SYSTEM_MONITOR_ENABLED`; não há `image` nem `build`. O teste reproduzido com Docker Compose local v5.7.0 falha com o mesmo serviço tanto com como sem `--profile facial`, portanto retirar o perfil não corrige a causa.
- Docker somente-leitura encontrou zero containers Gemma em execução e um container em todos os estados. O container parado permanece preservado.
- O diretório de estado tem proprietário `ubuntu:ubuntu`, modo `0700`; o backup será guardado nele como arquivo exclusivo modo `0600`. `/var/backups/markina-gallery` é `root:root 0750` e não é gravável pela credencial SSH usada.

## Procedimento aprovado e guardas

1. Após CI verde e integração do script, disparar `app-compose-reconcile` somente em `main`, pelo ambiente protegido `production`; o job usa a credencial mutável de operação, sem ampliar a chave read-only do preflight.
2. O helper fixa o host e checkout, adquire sem espera o lock comum `/var/lib/markina-gallery/deploy-state/production-release.lock`, exige árvore limpa no baseline observado, confirma que `main` remoto coincide com o SHA do run e busca somente essa referência sem trocar o `HEAD`. Qualquer divergência encerra sem escrita.
3. O helper aborta também se houver marcador de tentativa ou se IDs/estados/saúde dos containers Markina em qualquer estado mudarem.
4. Exigir `origin/main`, SHA-256, proprietário/modo/tamanho e estrutura do overlay exatamente iguais ao inventário acima. Exigir que o serviço Gemma continue ausente dos containers em execução e que a única cópia encontrada seja a parada observada. Qualquer divergência encerra sem escrita.
5. Criar backup exclusivo no diretório de estado, verificar o hash da cópia, retirar apenas o bloco Gemma cujo mapa contém exclusivamente `environment.SYSTEM_MONITOR_ENABLED`, preservar todo o restante do arquivo e criar candidato temporário com proprietário/modo originais.
6. Executar `docker compose ... config --quiet` contra o candidato com o mesmo conjunto e ordem de manifestos/perfis da operação API/web. Se falhar, descartar o temporário e manter o original. Se passar, substituir atomicamente e validar novamente pelo caminho canônico. Se a validação final falhar, restaurar o backup atomicamente e confirmar o hash original.
7. Comparar snapshots de containers Markina antes/depois; exigir identidade inalterada, Gemma ainda parado e nenhuma alteração de serviços. Registrar hashes do original, backup e arquivo reconciliado, além de owner/mode. Não imprimir configuração resolvida nem valores de ambiente.
8. Executar o preflight oficial somente-leitura para o SHA atual de `main`. Só liberar o deploy se fingerprint, labels e hashes API/web, schema `20261113_0126`, saúde, HTTPS, portas e `FACIAL_PROCESSING_ENABLED=true` forem aprovados. Depois executar a aprovação `production` já autorizada e o workflow, que recria somente API/web.
9. Após o release, confirmar os IDs de imagem e versão exatos, `APP_ENV=production`, flag facial verdadeira, schema intacto, endpoints HTTPS saudáveis e identidade dos serviços/vizinhos preservada. Não ativar o backup automático nesta publicação.

## Resultado

Pendente. Até a validação deste procedimento e a repetição completa do preflight, nenhum arquivo persistente do host foi alterado e nenhum serviço de produção foi reiniciado.
