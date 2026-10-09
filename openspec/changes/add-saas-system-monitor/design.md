# Design

## Context

Base 8d02583 na worktree existente `invite-only-otp`, branch `codex/remote-test-campaign`. Mudanças preexistentes em fixtures e documentos de homologação não pertencem a este trabalho. O card usa cache de 30 s por processo e cinco agregações PostgreSQL; a permissão installation_operator não autoriza consultar identidades globais.

## Goals / Non-Goals

Entregar código utilizável após migration/configuração/publicação autorizadas. Nenhum servidor local, deploy, concessão real, alteração OCI, carga ou mudança nas campanhas. Testes unitários de funções/ORM em memória e Vitest não iniciam servidor; runtime remoto permanece gate próprio.

## Decisions

- PostgreSQL existente armazena buckets de um minuto, histogramas de limites fixos, snapshots e incidentes. Evita introduzir serviço pago ou daemon externo; custo limitado por operações fixas e retenção de 7 dias (configurável 1–30). Relatórios até 24 h, 1 MiB e número limitado de linhas. Percentis são limites superiores dos buckets, mínimos de 20/100 amostras para p95/p99, nunca médias de percentis.
- Instrumentação HTTP ASGI mede até o fim do corpo e agrupa operações fixas; buffers limitados e flush fora da resposta. Aquisição SQLAlchemy mede aquisição completa (incluindo conexão), não promete tempo puro na fila. Falha de telemetria não altera respostas de negócio. Instrumentação desligada por padrão até liberação de configuração.
- Coletor API periódico a cada 60 s usa lock PostgreSQL para um coletor por instalação, budgets SQL e snapshots sanitizados. Pool local continua explicitamente de um processo. Workers publicam sinal de ciclo e progresso; ciclo antigo sinaliza ausência de confirmação, não prova processo morto. Jobs terminais são agregados no banco em janela limitada. Duração de tentativa instrumentada é separada da idade do job.
- Permissões `metrics`, `tree`, `incidents`, `export` por administrador, revogáveis e vazias na migration. Toda rota revalida sessão/vínculo e permissão; export exige metrics + export e inclui incidentes somente com incidents. Operador do card antigo não recebe concessões implícitas. Auditoria guarda somente ação e ator.
- Árvore usa paginação por UUID, limit 25 máximo 100, busca limitada e filtro por estado. Fotógrafos são identificados por alias técnico da conta, clientes por nome somente na árvore privilegiada; export não inclui árvore, nomes ou IDs de negócio. Sessões são agregadas após expiração/revogação e conta/vínculo ativos. Uma mesma pessoa em contas distintas continua separada.
- Atividade vem de interação visível no frontend, POST autenticado sem payload, header obrigatório contra CSRF e limite de uma atualização/minuto por sessão. Sem polling de presença ociosa. Parâmetros iniciais: ativo 120 s, recente 1.800 s; são regras configuráveis, não presença física comprovada. Sem sinal, sessão válida permanece sessão válida; sem cobertura/frescor, desconhecido. Sinais individuais expiram após 24 h.
- Host: arquivo JSON com schema fechado, UTC, fonte/scope e métricas numéricas allowlisted, tamanho e idade limitados, montado somente leitura se autorizado. Coletor Linux stdlib opcional lê /proc e filesystem explicitamente escolhido, sem instalar agente, abrir porta ou ler Docker socket. Ausência da fonte não vira zero. Espaço de arquivos registrados, filesystem, provisionamento OCI e quota são campos distintos. OCI/IAM não são presumidos.
- Alertas persistentes por chave fixa, duração mínima 120 s, recuperação após nova evidência saudável e deduplicação; ausência de dados não fecha incidente nem declara indisponibilidade. Limiares iniciais configuráveis/documentados: erro 5% com >=20 requisições, p95 2 s com >=20 amostras, idade de fila 300 s, pool 90%, disco livre 10%. Coleta envelhecida é alerta de dados. Estado saudável exige evidência atual suficiente; sem host ou HTTP, cobertura parcial/desconhecida.
- Página /admin/system-monitor responsiva, gráficos SVG acessíveis, atualização 60 s somente visível, opção manual e seletiva da árvore, controles nativos e estados explícitos. Card antigo permanece nas duas superfícies sob sua própria capability.

## Risks / Trade-offs

### Detalhamento após implementação

Diretriz humana posterior: dados operacionais exclusivos da conta do proprietário, inicialmente identificada por `conradodeita@gmail.com`, incluindo os diagnósticos preexistentes. Propriedade em tabela singleton vinculada ao UUID imutável do administrador, sem e-mail fixo na autorização. Troca/verificação de e-mail na mesma conta mantém propriedade; reutilizar e-mail anterior em outra conta não transfere propriedade. Gate central no backend, revalidado antes/depois da consulta, com grants independentes mantidos. CLI offline admite somente indicação inicial explícita e recusa substituir proprietário existente. Migration permanece vazia; ativação real segue gate operacional. Testes com outra identidade mesmo portadora de grants SHALL negar os dados.

CPU >=90% e RAM disponível <=10% também geram alerta preventivo persistente, configuráveis. Saúde exige fonte atual do host com CPU/RAM/disco, HTTP e seções essenciais coletadas; cobertura parcial permanece explícita.

Fonte Linux entregue como CLI stdlib de duas leituras/1 s, JSON atômico e diretório privado; execução/agendamento/montagem permanecem autorização operacional própria. Inspeção SSH somente leitura confirmou procfs legível, agente consultado inativo e CLI OCI ausente; IAM/quotas não confirmados. Overlay Compose entregue inativo por padrão, sem portas ou recursos novos.

Inventário de bytes usa projeção de até 1.001 caminhos cadastrados e até 1.000 stats/hora/processo, budget cooperativo 1 s, cache próprio; total nulo se incompleto e limite inferior separado. Evita a varredura/listas completas dos coletores preexistentes. Escopo: originais e prévias convencionais/ajustadas; histórico comercial, staging e biometria excluídos e declarados. Timestamp do inventário não é atualizado pelo cache.

Falhas persistentes (default 3 registros) e rejeições de autenticação são alertadas além dos limiares anteriores; erro HTTP >=50% é crítico, sem declarar serviço totalmente indisponível. Worker/progresso são sinais de ciclo, com comparação a backlog conhecido, nunca prova de processo morto. Consultas administrativas limitadas a duas simultâneas/processo; auditoria de árvore e exportação somente do ator. Grants têm CLI offline com dry-run e aplicação explícita. Purga por lotes somente de tabelas técnicas, sem downgrade destrutivo.

- Buffers voláteis → perda limitada em crash declarada na qualidade da coleta, não telemetria financeira.
- Monitor compartilha PostgreSQL → timeout, buffer limitado, consultas indexadas e ausência de retry em loop. Falha de fonte preserva aplicação.
- Múltiplas réplicas → UPSERT atômico para contagens, lock para snapshots; pool não agregado como global.
- Atividade/nome de cliente → permissão separada, sem telefone/e-mail, cache no-store e exclusão da exportação.
- Instrumentação habilitada exige avaliação remota → documentar gate, não declarar capacidade ou implantação com base em testes unitários.

## Migration Plan

Validação CI: o teste do layout preserva botão de instalação único, toolbar global e conteúdo dentro de SessionBoundary, incluindo agora um único MonitorActivity. Após falha por quota anônima do Docker Hub no runner, os dois serviços PostgreSQL 17 Alpine do CI usam o espelho Docker Official Images no ECR Public (`public.ecr.aws/docker/library/postgres:17-alpine`). Versão principal, bancos sintéticos, portas e healthchecks permanecem iguais; nenhuma imagem de deploy é alterada.

Migration aditiva cria tabelas próprias, sem concessões nem alteração do domínio. Depois de aprovação operacional: inventário vigente, backup, migration, versão exata, configuração/permiteções offline, publicação e smoke remoto com contas sintéticas independentes. Desabilitar coleta reverte instrumentação; não executar downgrade destrutivo. Sincronizar/arquivar somente após revisão humana.
