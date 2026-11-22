# Inventário de backup — 06/11/2026

## Estado confirmado e correção do diagnóstico

A task 1.1c foi concluída por comparação somente de metadata. No Pick-your-Pic, as duas entradas imediatas do destino são exatamente as duas esperadas pelo estado `last-success.json`. No ClearBudget, o estado e o arquivo esperado estão presentes, mas existe uma entrada adicional. Nenhum objeto foi removido, promovido ou restaurado. Correspondência de nomes não comprova checksum, conteúdo, independência ou recuperação.

O diagnóstico anterior de credencial systemd ausente estava incorreto. A leitura estruturada via D-Bus, como root, confirmou `LoadCredential` com assinatura `a(ss)` e **zero entradas**. A saída textual de `systemctl show` havia sido interpretada indevidamente como um identificador. Estão retiradas as conclusões de que o operador precisaria corrigir uma credencial systemd ou instalar `systemd-creds` para esta consulta. O host usa systemd **249**; `systemd-creds` não estava disponível na consulta. O executável selecionado é `/usr/bin/rclone`, versão **1.53.3**, sem alternativa em `/usr/local/bin/rclone`.

## Fontes versionadas locais

| Fonte | Finalidade comprovada | Limite para o SaaS |
|---|---|---|
| `scripts/deploy-homolog.sh` | Dump PostgreSQL custom e manifesto pré-deploy de homologação. | Proteção de release, sem política recorrente ou restore por tenant. |
| `scripts/deploy-prod-infinitepay-retirement.sh` | Dump, catálogo e recibo de restore conforme release. | Gate de operação específica; não é serviço SaaS recorrente. |
| `scripts/maintain-homolog-data.sh`, `scripts/operate-facial-rollout-homolog.sh` | Dumps de segurança antes de ações autorizadas. | Escopo operacional pontual. |
| `scripts/orders_pilot_release.py`, `scripts/preview_adjustment_migration_release.py` | Dumps de preparação de migration. | Rollback de release, sem provar cópia independente. |
| Módulos `app_env_transition`, `environment_transition_bundle`, `combined_environment_transition` | Pacotes cifrados/autenticados de transição de configuração. | Não abrangem a plataforma completa. |
| `facial/environment_backup.py`, `facial/environment_sql_backup.py` | Pacotes biométricos restritos a migrações de ambiente. | Não substituem backup global ou de arquivos operacionais. |

O Compose declara volumes de PostgreSQL, Redis, mídia-fonte, derivados, histórico, branding, biometria e WhatsApp, mas não serviço de backup. Não foi identificado job SaaS recorrente no worker nem nos workflows versionados examinados. A menção no `scripts/README.md` a scripts PostgreSQL→Drive futuros não é inventário completo dos scripts atuais.

## Autorização e método de consulta

O proprietário autorizou SSH de consulta, leituras estáticas limitadas do job, comparação de metadata dos dois destinos, tentativa transitória de listagem e diagnóstico filtrado, com continuidade posterior. A operação permaneceu limitada a inventário e reconciliação: sem executar o job de backup, alterar units, reiniciar serviços, mudar secrets persistentes, escrever/remover objetos remotos, abrir arquivos de backup ou consultar dados de cliente.

Os localizadores conhecidos são `/usr/local/lib/oracle-project-backups/project_backups.py` e `/etc/oracle-project-backups/rclone.conf`; os aliases são `pyp_backup:` e `clearbudget_backup:`. Código, configuração e logs brutos não foram devolvidos ao executor nem salvos como evidência. O rclone carregou sua própria configuração internamente.

A leitura estática autorizada de `backup()`/`remote()` identificou comparação entre nomes de `entries` e o conjunto esperado derivado de `old["archive"]`, acrescido de `last-success.json`; sem estado anterior, o esperado é vazio. O documento de estado é metadata do job e foi lido somente para essa comparação, com limite de 128 KiB. Nenhum arquivo de backup foi baixado.

## Inventário remoto do host

- `oracle-project-backups.timer`: última ativação observada em 06/11 às 03:01 -03 e próxima em 07/11 às 03:09:44 -03.
- Serviço descrito para Pick-your-Pic e ClearBudget: `ActiveState=failed`, `Result=exit-code`, `ExecMainStatus=1`; execução de 03:01:22 a 03:15:34 -03 de 06/11.
- Journal dessa janela: 14 mensagens processadas por filtro; 3 mencionam Pick-your-Pic/Markina, 2 ClearBudget/Firefly. Duas ocorrências de `RuntimeError` e duas de `interrupted candidate needs reconciliation`; sem atribuição segura da exceção por projeto. Nenhuma linha bruta foi emitida.
- Containers Markina de API, web, worker, PostgreSQL, Redis, WhatsApp e mídia estavam em execução; vários reportavam `healthy`. Componentes ClearBudget, Nginx Proxy Manager e Portainer também estavam em execução. Isso é inventário, não teste funcional.
- Portas observadas: NPM 80–81/443; Nginx do produto `127.0.0.1:8080→80`; frontend ClearBudget 3000→80; Portainer 8000/9000/9443. Alcance externo e firewall não foram consultados.
- Volumes nomeados do produto, Portainer e volumes anônimos foram inventariados sem abrir mounts/conteúdo.
- Os nomes dos arquivos cron examinados eram de sistema/pacotes; o conteúdo e outros agendamentos não foram lidos.

## Tentativas anteriores e limite da proteção

As primeiras listagens retornaram uma categoria sanitizada genérica de configuração. A tentativa de helper transitório não produziu listagem; a classificação `credential_materialization` não constitui diagnóstico válido de autenticação do serviço. Não houve unit persistente, e `matching_units=0` confirmou que nenhum helper permaneceu carregado.

A busca filtrada no journal do helper encontrou dois registros de prioridade 5 sem categoria fixa de falha/ciclo de vida; ela não explicou a tentativa. As buscas de arquivos usando o suposto identificador não demonstravam falta de segredo, pois a premissa do identificador estava errada.

O isolamento anterior montava somente o arquivo de configuração como read-only. Isso protege o arquivo original, mas deixa seu diretório pai gravável; não há evidência suficiente para afirmar que nenhum arquivo temporário tenha sido criado/removido durante essas tentativas. Nenhum resíduo foi apagado.

O [fonte oficial do rclone 1.53.3](https://github.com/rclone/rclone/blob/v1.53.3/fs/config/config.go#L478-L573) mostra que a persistência usa arquivo temporário e renomeação, e que falha em `SaveConfig()` pode encerrar o processo. A falha observada era compatível com a proteção usada pela consulta; não foi comprovada revogação de token, falta de segredo, corrupção ou falha do provedor.

## Reconciliação concluída com camada em memória

A consulta bem-sucedida usou namespace privado de montagem. O diretório original foi montado como camada inferior read-only; upper/work/cache do overlay ficaram em tmpfs. O rclone pôde regravar sua visão da configuração somente em RAM. A camada desapareceu ao terminar o processo, sem persistir tokens ou mudar o serviço.

Foram executadas listagens imediatas, sem recursão, `--no-modtime`, `--no-mimetype` e sem hashes. Apenas `last-success.json`, quando presente e dentro do limite, foi aberto como metadata. A saída foi reduzida a contagens e booleanos; nomes, IDs, valores do estado e secrets não foram emitidos.

| Projeto | Entradas | Esperadas | Faltantes | Extras | Arquivo do estado presente | Correspondência |
|---|---:|---:|---:|---:|---|---|
| Pick-your-Pic | 2 | 2 | 0 | 0 | Sim | Exata |
| ClearBudget | 3 | 2 | 0 | 1 | Sim | Divergente |

Evidência do isolamento: `source_directory_read_only=true`, `temporary_layer_tmpfs=true`, `overlay_mounted=true`, `memory_config_was_rewritten=true`. O snapshot de nomes/inodes/tamanhos/mtime/modos do diretório original permaneceu igual durante **essa consulta bem-sucedida**: `source_directory_metadata_unchanged=true`. Esse check é de metadata; não foi calculado hash ou lido conteúdo de segredo.

A entrada adicional do ClearBudget é compatível com a proteção de reconciliação observada no fonte, mas a comparação atual não prova a causa histórica exclusiva da execução falha. Não foi feita correção em outro projeto.

## Recuperabilidade e pendências

O checkpoint histórico de 02/11 registrou um candidato Pick-your-Pic marcado `verified` e falha na sequência multi-projeto. Ele não comprova o estado atual nem recuperação de aplicação, privilégios, mídia, filas ou chave/volume OCI.

As tasks 1.1a/1.1b/1.1c estão concluídas dentro dos limites descritos. O proprietário aprovou a política global e o escopo inicial em 06/11/2026, registrados em `policy-decision-draft.md`; a task 1.2 está concluída e o desenho 2.1 foi validado por OpenSpec strict. Google Workspace foi escolhido para a segunda cópia, com identidade dedicada na rotina e conta do proprietário somente no ensaio pré-abertura. A implementação local pode avançar sem mudar produção. Quota/destino/permissões reais, credenciais, checksum e restore externos permanecem sem validação.
