# Design: backups e recuperação global da plataforma

## Context

Política aprovada pelo proprietário em 06/11/2026, após esclarecer que os valores são globais: cópia diária, RPO alvo de 24 h, RTO alvo de 8 h ainda não medido, retenção 7 diários/4 semanais/3 mensais e ensaio mensal. Escopo PostgreSQL completo e configurações essenciais cifradas; classes pessoais, financeiras e biométricas existentes no banco incluídas. Arquivos de mídia/biometria/WhatsApp e restore lógico por tenant ficam para etapa posterior. Chave de recuperação offline do proprietário; Google Workspace foi escolhido para a segunda cópia, com identidade dedicada na rotina e conta do proprietário somente no ensaio pré-abertura. Quota/destino/custódia efetivos e chamadas reais seguem pendentes.

O inventário de metadata foi concluído sem abrir backups: Pick-your-Pic 2/2 sem diferenças; ClearBudget 3/2, uma extra preservada. Isso não valida conteúdo, restauração ou independência. A hipótese de credencial systemd ausente foi retirada; a inspeção rclone só funcionou quando suas escritas locais ficaram em overlay/tmpfs.

## Goals / Non-Goals

Implementar e ensaiar localmente o pacote global, catálogo durável, agenda, cópias retomáveis, verificação e recuperação isolada. Metas de RPO/RTO aparecem como metas, sem declaração de SLA. Não conectar a produção, modificar o job externo, importar backups reais, configurar secrets, criar rotas públicas ou apagar mídia/objetos existentes.

## Decisions

### Reaproveitamento e separação de domínio

- Reutilizar a dependência `cryptography` já declarada e o padrão AES-256-GCM com AAD contextual e erros sanitizados. Pacotes de transição/faciais existentes autenticam snapshots pequenos em memória e têm contextos de migração próprios; não serão convertidos em backup global nem alterados.
- O store POSIX dos pacotes faciais exige JSON limitado e arquivo de chave por operação, contrato diferente de streams e chave offline. Suas funções privadas não serão importadas ou generalizadas sem necessidade; preservar consumidores especializados.
- `google_drive_storage.upload_drive_file` continua sendo o único helper de envio real Drive, production-only. Esta implementação define uma fronteira de armazenamento substituível e valida somente stores locais sintéticos; não duplica OAuth/HTTP, não usa rclone e não simula uma integração Google real.
- Não acrescentar tabelas ao banco que está sendo protegido. O catálogo do coordenador é filesystem privado, fora dos dados ativos, para permitir recuperação quando o PostgreSQL estiver indisponível. Não há migration da aplicação nesta etapa.

### Proveniência e arquivo cifrado

- UUID de instalação e UUID do backup, revisão de schema, ambiente e instante UTC compõem um cabeçalho de versão fixa, sem PII, caminhos, IDs remotos ou secrets. O JSON canônico do cabeçalho é AAD; identidade/schema divergentes são recusados.
- Pacote interno contém dump custom PostgreSQL, manifesto e configuração essencial explicitamente fornecida. Manifesto cifrado registra nomes lógicos allowlisted, tamanho e SHA-256 de cada membro; nunca extrair nomes arbitrários, symlinks ou caminhos vindos de arquivo.
- AES-256-GCM em streaming, nonce aleatório de 96 bits e tag de 128 bits; usar a API Cipher/GCM da biblioteca existente. Limite técnico inicial de 32 GiB por arquivo cifrado, abaixo do limite por mensagem do GCM; não carregar o dump inteiro na memória.
- Chave de 32 bytes é injetada pelo chamador, nunca persistida pelo módulo, retornada, incluída no pacote ou lida de secrets reais. Produção e outros ambientes protegidos são recusados nesta implementação local.
- A abertura decifra somente para staging privado. Nenhum byte é entregue ao restaurador antes da autenticação completa da tag, do fim do arquivo e do manifesto. Pacotes truncados, adulterados, de outra instalação/schema/ambiente ou com chave errada falham sem escrita no destino de recuperação.
- Receipt externo contém somente UUID, versão, tamanho e SHA-256 do ciphertext. Secrets e hashes de membros permanecem no conteúdo cifrado.

### Estado persistente e agenda

- Catálogo privado POSIX, owner atual, diretórios 0700 e arquivos 0600, caminhos sem symlink. Eventos append-only por backup, sequência/encadeamento verificáveis e fsync; não sobrescrever histórico para promover estado.
- Estados distinguem preparação, cópia parcial, enviada, reaberta, restore comprovado e falha. Envio não promove a recuperável. Erros registram somente código constante e instante UTC.
- Agenda diária usa chave UTC do dia e eleição exclusiva; retry retoma o mesmo backup/artefato, sem produzir outro snapshot sob a mesma identidade. Trabalho interrompido exige validar artefato/checkpoints; origem alterada não é silenciosamente aceita.
- Worker é operação interna local explícita. Não ligar ao worker de produção, systemd, cron ou Compose nesta etapa.

### Cópias e retomada

- Store tem identidade e domínio de falha explícitos; testes usam diretórios distintos e domínios sintéticos. Isso não prova independência de contas/provedores reais.
- Objeto final é imutável por UUID. Parcial persistido pode retomar somente após conferir comprimento e prefixo com o mesmo ciphertext/checksum. Conflito, quota ou autenticação falham sanitizados; nenhuma cópia antiga é apagada para liberar espaço.
- Após envio, reabrir e conferir SHA-256/tamanho do ciphertext e autenticar o pacote. Um receipt de upload isolado não basta. Ensaio de restore global fica registrado como prova separada vinculada ao mesmo objeto/schema.

### Recuperação global isolada

- Autenticar e validar todo o conjunto antes de chamar pg_restore. Destino deve ser explicitamente descartável, identificado e vazio, com revisão suportada; rejeitar origem, ambientes protegidos e alvo preexistente.
- Operador local de PostgreSQL usa pg_dump custom e pg_restore com `--exit-on-error`; privilégios/roles/configuração são inventariados no pacote. Não executar SQL de roles ou configurar secrets automaticamente fora do destino descartável.
- Verificar schema e invariantes do banco restaurado e permitir conferência sintética de tenants/financeiro. Falha não autoriza sobrescrever origem ou outro banco.
- Restore por tenant não é oferecido. Configuração cifrada pode ser reaberta para conferência em staging; não aplicar chaves/canais/integrações em runtime.

### Retenção e gates externos

- Selecionar união dos 7 dias, 4 semanas ISO e 3 meses mais recentes com ponto válido por período, sem duplicar cópias por tenant ou apagar dados ativos.
- Uma exclusão local simulada exige outra cópia independente do mesmo conjunto com restauração comprovada, receipt íntegro e preservação do último ponto recuperável. O planejador nunca deleta por conta própria; qualquer expurgo real permanece bloqueado.
- O planejador usa os períodos UTC mais recentes representados, sem descartar pontos apenas por falhas/dias sem backup, e preserva adicionalmente o ponto recuperável mais recente. A remoção de uma cópia local exige confirmação explícita vinculada ao UUID do backup/destino, cópia sobrevivente de outro domínio/raiz e recibo assinado correspondente ao ciphertext/schema. Ambas as cópias ficam sob locks adquiridos em ordem estável; reabertura e autenticação do sobrevivente precedem unlink do candidato. Nenhum scheduler chama essa operação e ela não implementa expurgo de provedores reais ou exclusão de todas as cópias de um conjunto antigo.
- Consentimento/permissões Drive, cadastro da identidade dedicada, quota/destino real, chave real e ensaio externo são gates operacionais pendentes. A indisponibilidade deles não bloqueia contratos locais independentes, mas impede declarar recuperação integral/produção pronta.

## Risks / Trade-offs

- Streams GCM precisam autenticar antes de liberar plaintext: staging privado e finalize obrigatório; testes de alteração/truncamento são gates.
- Catálogo fora do banco precisa ser durável e auditável: fsync, eventos sem sobrescrita, validação de sequência e retry idempotente; perda do catálogo não autoriza expurgo.
- Escopo inicial não inclui arquivos: mesmo restore global do banco não representa recuperação integral de fotos/biometria/WhatsApp.
- Independência sintética não equivale à real; Google Workspace está escolhido, mas identidade dedicada, quota, pasta/permissões e restore externo seguem pendentes.
- Não executar código não confiável de dump sem autenticação e destino isolado.

## Migration Plan

Nenhuma migration ou configuração de produção. Todo artefato local, dump sintético e catálogo de teste fica fora do Git em raiz privada descartável. Na validação Linux, usar somente containers novos com rótulo de teste, imagem local existente, código read-only, tmpfs, nenhuma porta pública e nenhum mount de dados dos serviços existentes. Docker ativo observado: `desktop-linux`; os containers preexistentes de UI/subdomínio e WhatsApp serão preservados. Testes de PostgreSQL terão rede/container exclusivos e dados sintéticos; inventário próprio precederá sua criação.

## Validation Plan

Provas de streaming com leitura limitada; round-trip e recusa de chave/contexto/schema/tamper/truncamento; catálogo/retry/concorrência; falhas de cópia/quota/autorização/checksum/retomada; retenção sem última cópia; restore real de PostgreSQL sintético em destino vazio, preservando outro banco/tenant. OpenSpec strict, Ruff e testes focados antes de concluir cada task. Validação externa real é gate pendente e não será contada como teste local.

## Plano de ensaio PostgreSQL local

O ensaio de 2.3 usará containers novos de origem/destino, imagem PostgreSQL 17.11 já local, contexto Docker `desktop-linux` com endpoint local, rede `none`, nenhuma porta publicada, nenhum volume persistente e PGDATA em tmpfs. Labels de escopo, papel e UUID do ensaio e IDs completos serão verificados antes de cada operação. Containers preexistentes não são alvo. A limpeza verificará os mesmos IDs/labels e removerá somente esses recursos sintéticos.

O adapter de ensaio não aceita DSN, host, usuário ou nome de banco arbitrários: verifica contexto/labels, nomes sintéticos e destino vazio. `pg_dump -Fc` ocorre somente na origem sintética; `pg_restore --exit-on-error --single-transaction` somente no destino sintético. Nenhum `--clean`/`--create` ou operação de banco alheio. Schema e ownership serão conferidos após restore; um banco sentinela distinto comprovará preservação. Configuração cifrada é reaberta/validada, nunca aplicada ao runtime.

O restore é uma fronteira injetável independente de storage: checksum do ciphertext, GCM e manifesto completos antes de inspecionar/restaurar o alvo. Recibo de restore vincula backup, hash, schema e UUID do destino e só pode promover a cópia previamente verificada. O worker POSIX é ensaiado separadamente com producer sintético; o ensaio PostgreSQL no host usa as mesmas primitivas de pacote/cifragem/restore e um adapter Docker explicitamente local, sem montar socket no container Python ou ler dados existentes.
