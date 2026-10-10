# Monitor do sistema

Implementação: change `add-saas-system-monitor`, migration `20261009_0072`, publicada em homologação no SHA `777495b012bb98174e50c07b15dd507b329b8de4`. Painel em **Administração → Monitor do sistema**, `/admin/system-monitor`. Propriedade/grants e coleta foram ativados com autorização operacional; a configuração padrão continua opt-in. Validação visual autenticada concluída no SHA 3bdc362 em 10/10/2026.

## Autorização e privacidade

O backend exige sessão administrativa válida, e-mail verificado, vínculo único ativo e concessões independentes: `metrics`, `tree`, `incidents`, `export`. Exportação exige também `metrics`; incidentes entram no relatório somente com `incidents`. `installation_operator` continua autorizando exclusivamente o cartão antigo. Nenhum grant é criado na migration.

Diretriz posterior do proprietário: **somente a conta proprietária da SaaS** pode acessar monitor e diagnósticos operacionais, mesmo que outro administrador tenha grants. A tabela singleton `platform_owner` vincula propriedade ao UUID do administrador; o e-mail atual serve apenas à identificação inicial. Trocar/verificar o e-mail na mesma conta preserva a propriedade; uma nova conta com o e-mail antigo não recebe acesso. `installation_operator` também passa a exigir essa propriedade para capacidade e diagnóstico facial. A migration não elege ninguém automaticamente. Proprietário ainda precisa dos grants explícitos; o CLI recusa transferência para outro UUID, que exigiria decisão operacional própria.

Árvore global é privilégio da administração SaaS: clientes são consultados por tenant, sem telefone/e-mail, com nome somente nesta superfície. Contas recebem alias de UUID público. Consulta da árvore e exportação geram auditoria do ator, sem critérios de busca, nomes consultados ou conteúdo do relatório. Respostas privadas usam `no-store`, incluindo erros via middleware. Sessão e concessão são revalidadas após consulta. Logout/revogação limpam dados da interface e cancelam downloads pendentes.

Concessão offline futura, em ambiente autorizado e com configuração segura já disponível:

```sh
python -m app.system_monitor.grants --admin-id <UUID> --permission metrics --permission tree --permission incidents --permission export --authorization-reference <REFERENCIA>
# Na indicação inicial, acrescentar --establish-owner-email <EMAIL_ATUAL_CONFIRMADO>.
# Esse e-mail confirma a conta indicada por UUID; não se torna regra de autorização.
# O comando acima faz dry-run e rollback. Somente após autorização:
python -m app.system_monitor.grants --admin-id <UUID> --permission metrics --authorization-reference <REFERENCIA> --apply
# Revogar uma concessão usa os mesmos parâmetros e --revoke --apply.
```

Na ativação autorizada, a conta identificada pelo e-mail confirmado recebeu propriedade por UUID e as quatro concessões. A operação foi auditada com referência `owner-approved-monitor-20261009`. Configuração do monitor fica em overlay privado separado; `.env` e segredos não foram editados.

## Coleta, limites e semântica

| Sinal | Fonte e limite | Interpretação |
|---|---|---|
| HTTP | ASGI até fim do corpo; operações fixas | Requisições, 5xx, 4xx e latência; não mede renderização do navegador nem erros no Nginx antes da API |
| Pool | SQLAlchemy QueuePool da API e workers | Aquisição completa incluindo conexão; timeouts contados separadamente das demais falhas. Não representa tempo puro em fila |
| Processamento | Ciclos instrumentados + estados agregados no SQL | Duração de ciclo/tentativa; falhas capturadas internamente aparecem nos estados de jobs, não necessariamente como exceção do ciclo |
| Filas/banco | Coletor existente + `pg_stat_activity` | Pool instantâneo continua de um processo API; conexão PostgreSQL do banco inclui outros consumidores |
| Workers | Heartbeat por ciclo e último ciclo com trabalho | Observado não prova capacidade; ciclo antigo não prova processo morto, inclusive em trabalhos longos |
| Uploads/integrações | Estados agregados de lotes/entregas | Não lê destinatário, conteúdo, provedor nem texto de erro; falhas HTTP também são agregadas |
| Arquivos | Até 1.001 registros e 1.000 verificações de metadados/hora/processo, budget cooperativo de 1 s | Originais, prévias convencionais e ajustadas cadastradas; sem leitura de conteúdo ou varredura de diretórios. Se incompleto, total é nulo e limite inferior verificado é separado. Histórico comercial, staging e biometria ficam excluídos |
| Host | JSON fechado de até 16 KiB | CPU/RAM/filesystem/rede/I/O; ausência, sem permissão, futuro, valor inválido e idade tratados explicitamente |

Buffers de até 4.096 combinações minuto/operação/faixa, flush a cada 30 s, batches de até 100 UPSERTs atômicos. Snapshot global a cada 60 s com advisory transaction lock PostgreSQL. Consultas SQL: timeout 500 ms e lock timeout 100 ms; no máximo duas consultas administrativas concorrentes por processo. Fontes têm transações independentes, sem retry agressivo. Falhas são logadas com código fixo. Contadores de perda/falha são do processo coletor; perdas em crash e perdas de outros processos podem não ser quantificadas.

Histórico: buckets UTC de 1 min; HTTP agrupado em 5 min; até 120 snapshots, 200 transições e 100 alertas ativos por resposta. Relatórios JSON/texto até 1 MiB e 5–1.440 min, com minutos completos. Versão somente SHA hexadecimal de `APP_VERSION`; ambiente somente allowlist de `APP_ENV`. Percentis são limites superiores de histograma, p95 requer 20 amostras e p99, 100; overflow acima de 60 s não tem limite superior finito e fica nulo. Não somar requisições e ciclos de worker. Falta de amostras não é zero nem garantia de saúde.

Os coletores existentes de arquivos carregam registros completos/varrem diretórios; por isso o monitor usa uma projeção limitada própria e reutiliza as regras de raiz/namespace. Inventário é uma observação ao longo do ciclo, não snapshot transacional de disco. O filesystem real vem do host, enquanto provisionamento/quota OCI permanecem desconhecidos até verificação própria.

## Atividade e árvore

O navegador consulta política uma vez ao entrar em contexto protegido e sinaliza `pointerdown`/`keydown` com página visível, no máximo uma vez por minuto. Não há heartbeat ocioso. Backend aceita somente sessão atual e cabeçalho customizado; update por sessão também é limitado a 60 s. Cliente não envia relógio/identidade. Retenção dos sinais: 24 h.

- **Ativo agora:** sessão válida e sinal nos últimos 120 s.
- **Atividade recente:** sinal de até 1.800 s com sessão ainda válida.
- **Sessão válida:** sessão válida sem sinal nessa janela.
- **Sem atividade recente:** sem sessão/sinal válidos sob coleta atual.
- **Desconhecido:** coleta desligada, ausente, futura ou antiga (>180 s).

Essas janelas são regras configuráveis, não presença garantida. Sinais podem estar ausentes em clientes antigos/offline. A árvore usa cursor UUID, 25 registros por página (máximo 100), pesquisa de até 80 caracteres, filtro antes do limite e carregamento dos clientes somente ao expandir. Totais globais e falhas dos tenants da página são agregados SQL; não se consulta cada cliente separadamente. A árvore não acompanha o polling das métricas.

## Configuração e alertas

Variáveis prefixadas por `SYSTEM_MONITOR_`, com defaults propostos para ativação aprovada:

| Sufixo | Padrão | Limites |
|---|---:|---|
| ENABLED | false | Somente `true` habilita coleta |
| RETENTION_DAYS | 7 | 1–30 dias |
| ACTIVE_SECONDS / RECENT_SECONDS | 120 / 1800 | 60–300 / 600–3600 |
| STALE_SECONDS | 180 | 120–600 |
| ALERT_SECONDS | 120 | 60–900 |
| ERROR_PERCENT | 5 | 1–100; mínimo 20 amostras |
| LATENCY_MS | 2000 | 100–60000; p95 com 20 amostras |
| QUEUE_AGE_SECONDS | 300 | 60–3600 |
| POOL_PERCENT | 90 | 50–100 |
| DISK_FREE_PERCENT | 10 | 1–50 |
| FAILURE_COUNT | 3 | 1–1000 registros com falha |
| CPU_PERCENT | 90 | 50–100 |
| MEMORY_FREE_PERCENT | 10 | 1–50 |

Alertas têm chave fixa, estado pendente/ativo/resolvido, duração mínima e transições deduplicadas. Erros/falhas registrados são evidência confirmada da operação; saturação/latência/idade são preventivos; worker/host antigo é lacuna de dados. Erro HTTP persistente >=50% indica crítico, sem concluir indisponibilidade total. Evidência ausente não resolve incidente. Falhas de jobs são estados de registros atualizados nos últimos 5 min; integração usa estado atual. Não há monitor externo de disponibilidade nesta change; queda da coleta fica desatualizada/desconhecida.

Retenção remove somente tabelas do monitor: até 1.000 registros por tabela/ciclo e 10 minutos antigos de buckets/ciclo. A purga acompanha backlog gradualmente; não é prazo rígido se coleta estiver desligada. Incidentes ativos permanecem enquanto não houver recuperação observada. Não há envio de mensagens externas.

## Host: integração disponível e pendências

Inspeção SSH somente leitura em 09/10/2026 no servidor autorizado: `/proc/stat`, `/proc/meminfo`, `/proc/net/dev` e `/proc/diskstats` legíveis; `oracle-cloud-agent` consultado retornou `inactive`; CLI `oci` não foi encontrada. IAM/quotas e métricas OCI não foram confirmados. Treze containers do projeto foram listados; nenhuma instalação, alteração ou requisição de carga foi feita.

Foi entregue `backend/app/system_monitor/host_collect.py`, executável com Python stdlib no Linux, incluindo Python 3.8 do host Oracle. Comando efetivamente configurado no servidor autorizado:

```sh
python3 /var/lib/markina-gallery/deploy-state/host_collect.py --scope host --filesystem / --interface enp0s6 --device sda --output /var/lib/markina-gallery/system-monitor/host.json
```

O comando faz duas leituras separadas por 1 s e troca atômica do JSON. Sem interface/dispositivo explícitos, rede/I/O ficam nulos; não agrega bridges/veth/partições duplicadas. Disco livre é o disponível ao usuário do coletor. Scheduler configurado: timer `markina-gallery-system-monitor-host.timer` a cada 60 s, arquivo 0600 em diretório 0700 e bind somente leitura na API em `/run/markina-system-monitor`. A cópia standalone corrigida instalada no estado operacional tem SHA256 `74a8163329c79a036b9d6be70d413de8fb5af1a344f973173c7ab537c28ee3c9`; seu uso preserva checkout remoto limpo durante a publicação da correção de compatibilidade. O filesystem `/` corresponde ao dispositivo da mídia nesta instalação. Outro container/instalação deve declarar seu escopo real e configurar caminhos/permissões explicitamente.

Overlay `docker/docker-compose.system-monitor.yml` propaga configuração opt-in a API/workers. A ativação usa também `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`, arquivo privado 0600 que habilita os seis processos e monta o diretório de snapshot somente leitura na API. Combinar ambos com compose base, persistência de branding e preview-adjustment. O wrapper de deploy preserva o monitor quando ambos os arquivos existem e fornece `APP_VERSION` a partir do checkout efetivo, inclusive rollback. Depois de recriar a API, recriar o Nginx próprio para atualizar a resolução do upstream e verificar health interno/público. Não adicionar portas. Integração OCI futura pode produzir o mesmo contrato `source=oci_monitoring`; não existe cliente OCI implementado nem pressuposição de IAM.

## Estado final validado

Em 10/10/2026, workflow 38047039331 publicou o SHA 3bdc362 com sucesso. Schema 0072, 13 containers próprios healthy, seis processos com coleta habilitada, snapshot privado atualizado e versão correta. Fingerprint de terceiros preservado. A falha anterior de preflight foi corrigida incluindo a definição do worker opcional sem habilitar seu profile antes da detecção. Abertura e recarga autenticadas carregaram resumo, árvore e incidentes sem 429. Expansão/filtro, card e downloads JSON/texto sanitizados revalidados. Task 6.2 concluída; revisão humana aprovada em 10/10/2026, specs consolidadas e change arquivada.

Publicação inicial, migration, concessões e ativação foram autorizadas e executadas. Schema, lock PostgreSQL, fonte do host e negação HTTP anônima foram verificados no servidor. O proprietário realizou login normal; árvore, filtros/busca, exportação JSON/texto sanitizada e card foram exercitados. A interface coordena chamadas em fila serial compartilhada, sem ampliar limite no backend ou repetir pedidos automaticamente, mantendo cancelamento e progresso após falha. Compatibilidade/persistência/coordenação estão publicadas e validadas na instalação autorizada. Nenhuma credencial foi extraída nem sessão do proprietário fabricada. Reversão operacional: desabilitar coleta no overlay privado e retirar grants por CLI autorizado, preservando tabelas; downgrade destrutivo é recusado. Campanha A+B e recursos de terceiros permanecem preservados. Lacunas OCI/IAM/quotas, renderização no dispositivo, orçamento global e inventário incompleto não são zeros ou evidência de capacidade máxima.

Evidências e comandos executados: `openspec/changes/archive/2026-10-10-add-saas-system-monitor/validation.md`.

## Localização do diagnóstico sob demanda

A change `keep-capacity-diagnostics-in-system-monitor`, solicitada em 10/10/2026, retira o card **Diagnóstico sob demanda / Capacidade e filas** da Visão Geral. O card e sua ação Copiar relatório permanecem somente em **Monitor do Sistema**, sob as mesmas permissões e com consulta manual. Esta alteração está em preparação para PR/CI; sua publicação e validação remota ainda não foram concluídas. A evidência arquivada acima descreve o monitor antes dessa mudança de localização.

Identificação na árvore: o fotógrafo aparece como **Fotógrafo email**, usando o e-mail atual do único administrador com vínculo ativo na conta. Sem vínculo único, **Fotógrafo [e-mail indisponível]**. A busca aceita e-mail, sem misturar clientes entre contas. O e-mail é visível somente ao proprietário com grant tree e não integra métricas, auditoria de consulta ou exportações. Nenhum campo de nome foi criado, conforme orientação final do proprietário. Publicação/validação remota desse refinamento seguem pendentes do PR/CI.
