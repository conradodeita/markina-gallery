# Backup global — implementação e ensaio local

> **Aposentado em 25/11/2026.** O módulo e os instaladores descritos abaixo foram removidos na higienização; os comandos/testes desta página não devem ser executados. O documento permanece como histórico da tentativa. O substituto está em [`prove-open-source-backup-and-recovery`](../../openspec/changes/prove-open-source-backup-and-recovery/proposal.md) e inclui obrigatoriamente o fluxo existente de arquivo frio por fotógrafo.

## Escopo aprovado em 06/11/2026

Um conjunto global reúne o PostgreSQL de todos os tenants e configurações essenciais cifradas. A política é diária, retenção 7 diários/4 semanais/3 mensais, RPO alvo 24 h, RTO alvo 8 h a comprovar e ensaio mensal. Esses números não são cotas ou cópias separadas por fotógrafo. Arquivos de fotos, arquivos biométricos/WhatsApp e recuperação lógica por tenant ficaram para etapa posterior.

Os módulos em `backend/app/platform_backup/` são internos e locais. Não há rota de UI/API, cron, systemd, migration ou chamada no worker produtivo. Operações recusam `APP_ENV` protegido antes de IO. Configuração e chaves reais não são coletadas; o caller deve fornecer um snapshot e chave apropriados. Não execute com dados reais usando uma configuração de teste.

## Contratos

- `archive`: AES-256-GCM em blocos de até 1 MiB, arquivo máximo de 32 GiB, AAD com UUIDs de instalação/backup, ambiente, schema e UTC. Arquivo inválido nunca entrega handle decifrado ao restaurador. Chave não é persistida ou colocada no catálogo.
- `payload`: dump custom PostgreSQL, configuração explicitamente fornecida e manifesto dentro da cifragem. ZIP sem extração de paths; somente membros fixos, sem duplicação, symlink ou compressão. Hashes/tamanhos e contexto são conferidos antes de ceder o dump.
- `catalog`: diretório privado POSIX, eventos append-only com sequência e HMAC derivado por HKDF; índice diário assinado conserva o UUID para retries. Corrupção ou candidato parcial não autoriza recriar silenciosamente um snapshot diferente.
- `storage`: cópia sintética POSIX, parcial retomável somente com prefixo correto; publicação exclusiva, checksum e reabertura. Roots/domínios sintéticos distintos não provam contas/provedores independentes reais.
- `worker`: um tick diário explícito; producer injetado, arquivo cifrado reaproveitado no retry e falhas por destino preservadas. `copies_verified` significa reabertura/autenticação; não significa restauração comprovada.
- `restore`: checksum, GCM e manifesto completos antes do alvo. Somente destino descartável, vazio, atômico e diferente da origem. Configuração reaberta não é aplicada ao runtime. Recibo de restore é vinculado ao catálogo e à cópia correspondente.
- `postgres_sandbox`: adapter de ensaio que aceita somente Docker Desktop local, IDs/labels de escopo sintético, rede none e nenhuma porta publicada. Não aceita DSN/host/banco operacional arbitrários. O dump/restore real ocorre apenas nos containers criados pelo teste opt-in.
- `retention`: união dos períodos UTC 7/4/3, preservando adicionalmente o último ponto recuperável. O planejador não remove nada. A operação separada de descarte local exige confirmação vinculada a UUID/destino e outra cópia autenticada com prova assinada de restore; locks dos dois destinos impedem descartes cooperativos concorrentes. Não há expurgo remoto ou descarte de todas as cópias de um conjunto antigo.

## Testes

Na pasta `backend`, usando a virtualenv existente:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_platform_backup_archive.py tests/test_platform_backup_payload.py tests/test_platform_backup_restore.py
.venv/Scripts/python.exe -m ruff check app/platform_backup tests/test_platform_backup_*.py
```

Catálogo, store e worker dependem de POSIX; seus testes são executados em container Linux próprio com código read-only, tmpfs e sem rede/portas. Skips no Windows não constituem essa prova Linux. Não montar `.env`, socket Docker ou volumes operacionais no container Python.

O ensaio PostgreSQL exige opt-in explícito e cria dois containers locais novos com PGDATA em tmpfs, usando a imagem já disponível `postgres:17.11-alpine`, sem pull, rede, portas ou volumes persistentes:

```powershell
$env:PYP_BACKUP_POSTGRES_TEST = '1'
.venv/Scripts/python.exe -m pytest -q tests/test_platform_backup_postgres.py
Remove-Item Env:\PYP_BACKUP_POSTGRES_TEST
```

A fixture valida IDs e labels antes de remover somente seus próprios containers. Origem, destino, tenants, ledger, biometria e secrets do teste são sintéticos. Evidências e limitações em `openspec/changes/add-platform-backup-recovery/validation.md`.

## Componentes e compatibilidade observados

| Componente/origem | Constraint e consumidor | Runtime observado em 06/11 | Limite/risco |
|---|---|---|---|
| cryptography / projeto upstream e dependência já declarada | `>=44.0`, AES-GCM e HKDF do backup | Windows 48.0.0; Linux de ensaio 50.0.2 | Não houve upgrade de dependência ou nova avaliação de licença/avisos. Novos consumidores de criptografia exigem revisão humana antes de release. |
| Python / runtime já existente | Ruff alvo 3.12; módulos internos | Windows 3.12.9; Linux/ARM64 3.13.16 | Testes nesses runtimes; não declarar todos os runtimes de produção equivalentes. |
| PostgreSQL / imagem local `postgres:17.11-alpine` | CLI pg_dump/pg_restore e ensaio descartável | amd64, digest `sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b` | Dump e restore da mesma versão no teste; não valida outro major, schema ou roles reais. Licença/avisos não foram reavaliados nesta execução. |
| rclone / job externo já existente | Não é dependência do novo módulo | Oracle 1.53.3; somente diagnóstico autorizado de metadata | Nenhuma atualização aplicada, nenhum inventário de avisos efetuado. A falha do método de inspeção não autoriza mudar o job existente. |

Não houve consulta de advisories/licenças nesta etapa; isso não equivale a “sem vulnerabilidades”. Não foram adicionados pacotes nem alteradas imagens/runtime existentes.

## Gates de produção

Provedor/conta da segunda cópia, chave real sob custódia offline, consentimento/destino Drive, revisão de código e ensaio operacional permanecem pendentes. O helper Drive existente continua production-only e não foi duplicado. Nenhum resultado local autoriza deploy, mudança de agenda, expurgo real, restore sobre dados ativos ou exclusão da entrada adicional observada no ClearBudget.
