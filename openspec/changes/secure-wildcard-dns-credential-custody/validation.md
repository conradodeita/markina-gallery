# Validação — 07/11/2026

## Alcance

Somente scripts novos de laboratório e artefatos desta change. Não houve modificação em código de aplicação, segredo/configuração operacional, Oracle, DNS ou NPM compartilhado. O diff SaaS preexistente foi preservado. Não houve commit/push, sync de spec principal ou archive.

## Inventário reproduzível

- Docker Desktop `desktop-linux`; containers de teste PostgreSQL e serviços Evolution preexistentes preservados. Nenhuma porta nova publicada, nenhuma rede/volume persistente criado e nenhum prune.
- NPM 2.15.1 oficial, plataforma `linux/arm64`, índice OCI `sha256:52b2c59994f3d36acfcf70a1626f29734df0ed8c71bacc0269f78b6f939858bb`.
- Manifest ARM64 `sha256:a36f72b9b4a44b7ca64ecdb80d903a635f9fe80bc01a1d68e0d4d4bd1e01b0d5`; seu `config.digest` é `sha256:bd94715ff0d6f11047446b2c149d4adb45deaa8e18152b34befb13945b3dbd7b`, igual à identidade de imagem do inventário Oracle. Docker Desktop com store OCI apresenta o digest do índice/manifest em campos que não devem ser confundidos com esse config digest.
- Runtime observado no laboratório: Python 3.13.5, Certbot 5.6.0, cryptography 48.0.0. O metadata instalado declara cryptography `Apache-2.0 OR BSD-3-Clause`. Não houve pip install, atualização de dependências ou invocação Certbot/ACME.
- Container NPM rotulado `pyp.lab=wildcard-custody`, `NetworkMode=none`, `PortBindings={}`, limite de 1 GiB/2 CPUs; tmpfs `/data` 128 MiB, `/etc/letsencrypt` 64 MiB e `/tmp` 128 MiB. Sem socket Docker e sem cofre do emissor montados. Apenas o JWT sintético foi montado readonly; veja runbook.

## Testes de custódia/instalação

`/opt/certbot/bin/python3 -B -m unittest discover -s /repo/scripts -p test_wildcard_certificate_custody.py -v` em container ARM64 separado, `--network none --read-only`, tmpfs `/tmp` e somente três binds readonly (biblioteca, testes e cipher existente).

Resultado: **8 testes passaram, zero skips**, 0,611 s. Cobertura verificável no arquivo de testes:

| Contrato | Evidência |
| --- | --- |
| Repouso/materialização | token ausente no ciphertext; arquivo 0600/subdiretório 0700; limpeza ao sair |
| Referência/validade | chave incorreta, expiração e troca de referência cifrada recusadas; token não sintético recusado |
| Falha de emissão sintética | exceção do transporte sanitizada; arquivo removido e nenhuma instalação |
| Bundle inválido | nome exato markina recusado, validade curta, CA não confiável, chave divergente e PEM inválido preservam `current` |
| Destino restrito | raiz sem marcador e ponteiro com travessia recusados |
| Idempotência/concorrência | repetição não recarrega; duas instalações concorrentes resultam em uma instalação e um replay |
| Recuperação | falha de probe restaura bundle anterior; nova tentativa válida funciona |
| Falha da recuperação | código `recovery_failed` sanitizado, sem afirmar saúde; ponteiro anterior preservado |

Esses testes executaram no POSIX real do container; skips Windows não foram usados como prova de permissões. Não demonstram segregação de usuários operacionais, loader systemd, custódia offline ou recuperação de perda do host.

## Integração NPM

O primeiro ciclo completo passou: TLS confiando na CA sintética, SNI/hostname/fingerprint, renovação, replay e rollback após falha injetada de probe. Tabela `certificate` permaneceu vazia; token/chave privada ausentes no SQLite e logs examinados. Os dois hosts de referência mantiveram seus certificados próprios.

Repetição final passou também com monitoramento paralelo **sem retry** dos hosts de referência durante as trocas. Recibo sanitizado da execução final:

```json
{"result":"passed","npm":"2.15.1","tls_verified":true,"renewal_replay":true,"rollback_verified":true,"certificate_db_rows":0,"reference_hosts_unchanged":true,"issuer_vault_mounted":false,"reference_tls_probes":{"checks":16,"failures":0},"external_network":false}
```

Os 16 probes constituem amostra local de continuidade, sem tráfego de clientes ou carga representativa de produção. A renovação usa certificado novo de CA de teste, não solicitação à CA pública. O emissor é ensaiado no container unitário separado; o consumidor NPM recebe somente material sintético de certificado/chave. O operador confiável do laboratório liga os callbacks, sem conceder ao emissor acesso a Docker/API administrativa.

Achado corrigido no ensaio: OpenSSL/Python do digest exige AKI/SKI e KeyUsage na cadeia sintética. A fixture foi corrigida; verificação TLS permaneceu ativa, sem `CERT_NONE` ou desativação da checagem de hostname. A primeira tentativa sem esses campos foi rejeitada e não constitui evidência positiva.

O bootstrap RSA do NPM sob emulação ARM64 foi lento. A execução seguinte usou JWT exclusivamente sintético no formato nativo, sem modificar a imagem. A primeira tentativa antes de o backend estar pronto falhou antes de criar usuário; foi adicionado readiness limitado. Quando houve estado de teste preenchido, somente o container próprio foi recriado, sem alterar DB de serviços existentes.

## Revisão proporcional e gates

Reutilizado `IntegrationCipher.from_explicit_context`; nenhuma duplicação de cifra, leitura de keyring operacional ou alteração de `.env`. Os únicos consumidores dos novos módulos são testes/runner sintéticos. Não existe rota, worker, timer ou caller na aplicação. Nenhuma limpeza/refatoração de módulos preexistentes foi necessária.

Ruff dos três scripts, OpenSpec strict e `git diff --check` passaram na revisão final (este último emitiu somente avisos de conversão LF/CRLF em dois arquivos preexistentes). Os arquivos novos desta change também foram conferidos quanto a sintaxe e whitespace. Build frontend e suítes da aplicação não são exigidos por uma alteração que não toca esses consumidores; suas evidências anteriores não são apresentadas como revalidadas nesta change.

Descarte delimitado concluído: label, modo de rede e caminho absoluto temporário foram conferidos antes de remover somente o container NPM próprio e o arquivo JWT sintético/diretório vazio. Nenhuma imagem/cache foi removida. Os cinco containers preexistentes permaneceram `Up 2 days (healthy)` e com as mesmas portas ao encerrar; não houve reinício deles. O container unitário foi removido por `--rm`.

`runbook.md` documenta comandos/destinos fixos, retorno, descarte e gates pendentes. A aprovação desta implementação não aprova o helper operacional, store/recuperação reais, cadeia pública ACME, criação do token ou aplicação de ingressos. Nenhuma evidência deste laboratório equivale a SLA, medição de produção ou autorização de indisponibilidade.
