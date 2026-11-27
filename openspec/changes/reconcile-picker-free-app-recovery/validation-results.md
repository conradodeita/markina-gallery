# Evidência do ensaio da referência saudável atual

A exportação protegida #46008398565 passou na main `6b9fe6231b0885b5ccf544a8933c64afd2d917b8`. A CI de push #46002533051 passou. Os arquivos baixados foram conferidos por SHA-256 antes da importação.

## Identidade das imagens

O ID registrado pelo Docker do servidor é o hash da configuração da imagem. O Docker Desktop 29.9.3, com armazenamento containerd, importou pelo digest do manifesto OCI. A leitura do archive comprovou que o manifesto possui o digest esperado, aponta para a configuração cujo hash coincide com o ID do servidor e usa as mesmas camadas importadas. Nenhuma imagem alternativa foi construída para o ensaio.

## Ambiente e procedimento

- Docker context `desktop-linux`, projeto exclusivo `pyp-picker-proof-709294b2d5d3`.
- PostgreSQL 17.11 Alpine e Redis 7 Alpine já presentes localmente, banco e Redis em tmpfs.
- Imagens API/web ARM64 exportadas, executadas por emulação local.
- Rede Compose interna, sem publicação de portas. Serviços selecionados por projeto/arquivo exclusivos.
- `Base.metadata.create_all` do código da imagem criou 136 tabelas vazias. A tabela `alembic_version` sintética recebeu `20261113_0126`. Nenhuma migration foi executada.
- API em `APP_ENV=production`, com chaves e credenciais inteiramente sintéticas. OAuth sentinela montado em `/run/secrets/google-drive-oauth-client.json`, somente leitura. O arquivo do Picker não foi fornecido.
- Inicialização pelos comandos padrão das imagens. Probes internos `curl -fsS http://127.0.0.1:8000/health`, `wget -qO- http://127.0.0.1:3000/api/health` e `wget -qO /dev/null http://127.0.0.1:3000/` passaram.
- A conferência Docker confirmou imagem/manifesto correspondente, ausência de bind do Picker e OAuth montado somente leitura. O SHA-256 do sentinela permaneceu igual.
- Encerramento limitado ao projeto exclusivo com Compose `-p` e `-f` explícitos. Inventários completos de containers, redes e volumes ficaram idênticos antes/depois.

## Resultado e limites

O primeiro ensaio encontrou o ID de configuração sem referência direta no image store local. A equivalência OCI foi validada pelo conteúdo do archive. O primeiro smoke da API excedeu o prazo de 100 segundos sob emulação; a repetição com limite de 180 segundos passou. Os projetos temporários de ambas as tentativas foram removidos e seus inventários pré/pós coincidiram.

O ensaio comprova inicialização e saúde das duas imagens sem Picker e preservação do mount OAuth sintético. Não valida autenticação real no Google, inferência facial, dados de clientes, promoção em produção nem remoção do legado. A recuperação protegida ainda deve repetir o diagnóstico, comparar a fingerprint e validar os endpoints no host antes de publicar o recibo.

## Recibo sanitizado

```json
{
  "project": "pyp-picker-proof-709294b2d5d3",
  "images": {
    "api": "sha256:c0aed86f943e63f51b832c063f25e418e2537bab6ee3546656f5c0b56ef6df4a",
    "web": "sha256:d9dfa2dae3692688c93eebcb9daf9f988a48c9e4aa41ec391b276244ef88f7c6"
  },
  "source_run": 46008398565,
  "archives": {
    "api": "e0ced4a423bdb9edcb69b0247ec3b37da9ffd057e137722d2d5dd933d004f09e",
    "web": "0aba5e56bb43fa6d8afaa0da120c0a59bd89a337a4fbde240d0867af7a141e7c"
  },
  "local_manifest_ids": {
    "api": "sha256:edb58dfcbe1526d669b7c7aa4de475c2546f0b71def9137699e28a8a77751967",
    "web": "sha256:2363017698b6a3075a1f97ab698ae878b1daa419e871b91f50331beb81506e0f"
  },
  "synthetic_tables": "136",
  "api_health": "{\"status\":\"ok\",\"service\":\"api\"}",
  "web_health": "{\"status\":\"ok\",\"service\":\"web\"}",
  "web_root": "success",
  "oauth_sentinel_unchanged": true,
  "oauth_mounted_readonly": true,
  "picker_mount_absent": true,
  "network_internal": true,
  "result": "passed",
  "inventory_unchanged": true
}
```
