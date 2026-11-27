# Validação do tmpfs canônico de /run

O recovery #46011319633 abortou antes de preparar a troca com handoff_recovery_recipe_picker_mount_ambiguous. Os endpoints públicos /, /healthz e /api/health retornaram HTTP 200 depois da falha.

A chave SSH disponibilizada pelo proprietário foi usada em consultas somente leitura aos mounts Docker e aos campos volumes/tmpfs dos modelos privados ativos. A API possui tmpfs de /run e /tmp, bind exato do Picker e bind OAuth separado somente leitura. Nenhum conteúdo de credencial, configuração de ambiente ou dado de cliente foi consultado.

A correção preserva o tmpfs /run e suas opções somente quando existe um único bind Picker exato e OAuth exato somente leitura. Todos os demais casos de sobreposição continuam bloqueados. O diagnóstico passa a validar a receita antes de emitir fingerprint.

O ensaio isolado das imagens do run #46008398565 incluiu as opções de tmpfs observadas no modelo ativo. O banco temporário contém 136 tabelas vazias criadas por metadata, sem executar migrations. Rede interna e ausência de portas publicadas foram mantidas. Os comandos padrão das imagens iniciaram API/web; healthchecks e página inicial passaram. O arquivo Picker estava ausente e o OAuth sentinela permaneceu montado somente leitura e com conteúdo inalterado. O projeto temporário foi removido com projeto/arquivo Compose explícitos e o inventário pré/pós de containers/redes/volumes coincidiu.

A identidade das imagens foi conferida pelo SHA-256 dos archives e pelo vínculo entre manifesto OCI e hash de configuração original do Docker do servidor. O Docker Desktop containerd usa o digest de manifesto para selecionar a imagem local equivalente. O ensaio não comprova autenticação Google nem recuperação/retirada no host.

```json
{
  "project": "pyp-picker-proof-d0886fe912b7",
  "images": [
    {
      "service": "api",
      "config_digest": "sha256:c0aed86f943e63f51b832c063f25e418e2537bab6ee3546656f5c0b56ef6df4a"
    },
    {
      "service": "web",
      "config_digest": "sha256:d9dfa2dae3692688c93eebcb9daf9f988a48c9e4aa41ec391b276244ef88f7c6"
    }
  ],
  "source_run": 46008398565,
  "archives": [
    {
      "service": "api",
      "archive_sha256": "e0ced4a423bdb9edcb69b0247ec3b37da9ffd057e137722d2d5dd933d004f09e"
    },
    {
      "service": "web",
      "archive_sha256": "0aba5e56bb43fa6d8afaa0da120c0a59bd89a337a4fbde240d0867af7a141e7c"
    }
  ],
  "local_manifest_ids": [
    {
      "service": "api",
      "manifest_digest": "sha256:edb58dfcbe1526d669b7c7aa4de475c2546f0b71def9137699e28a8a77751967"
    },
    {
      "service": "web",
      "manifest_digest": "sha256:2363017698b6a3075a1f97ab698ae878b1daa419e871b91f50331beb81506e0f"
    }
  ],
  "synthetic_tables": "136",
  "api_health": "{\"status\":\"ok\",\"service\":\"api\"}",
  "web_health": "{\"status\":\"ok\",\"service\":\"web\"}",
  "web_root": "success",
  "oauth_sentinel_unchanged": true,
  "tmpfs_hardening_preserved": {
    "/run": "rw,nosuid,nodev,noexec,size=16m",
    "/tmp": "rw,nosuid,nodev,noexec,size=128m"
  },
  "picker_file_absent": true,
  "oauth_mounted_readonly": true,
  "picker_mount_absent": true,
  "network_internal": true,
  "result": "passed",
  "inventory_unchanged": true
}
```
