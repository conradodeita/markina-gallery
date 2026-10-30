# Diagnóstico de lentidão — Visão Geral em produção

## Escopo

Solicitação do proprietário: verificar a causa da demora da Visão Geral. Investigação somente leitura; nenhuma correção de produto, alteração de configuração, migration, reinício, deploy ou operação financeira. Mudanças locais da limpeza de testes anterior preservadas. Branch `feature/reconcile-mercadopago-release-evidence`, HEAD `86c808064906933c9cdc0e5e9b88d32ccceb385c`.

## Evidência no Chrome

Na sessão administrativa existente, navegação de Galerias para Visão Geral (`/admin`) mostrou primeiro `Preparando seu painel`, seguida do painel completo. Rede observada por CDP, sem leitura/exportação de cookies, headers, segredos ou payloads privados. Instrumentação Network desabilitada ao concluir.

| Requisição | HTTP | Duração |
| --- | ---: | ---: |
| `/api/admin/validation-summary` | 200 | 16.801 ms |
| `/api/auth/activity-policy` | 200 | 178 ms |
| `/api/auth/destination` | 200 | 189 ms |
| `/api/push/subscription` | 200 | 176 ms |
| `/api/branding/app-icon` | 200 | 308 ms |

Tempo até os headers do resumo: **16.764,82 ms**; transferência final consumiu uma parcela pequena. A interface em `frontend/app/admin/page.tsx` só exibe o conteúdo depois de receber o JSON inteiro desse endpoint. As outras chamadas no mesmo navegador não apresentaram demora semelhante.

## Perfil isolado no runtime publicado

Uma única execução da função existente `measure_owned_photo_storage`, em processo diagnóstico separado dentro da API, usando transação PostgreSQL READ ONLY e rollback. Somente o tenant explicitamente identificado nesta operação foi consultado. Instrumentação em memória do processo efêmero mediu SQL e funções sem alterar arquivos/processo servidor, autenticação ou controles de autorização. Não se executou a função de limpeza do módulo importado.

Medição instrumentada: **16.536,10 ms**, resultado disponível, **2.804.669.796 bytes**. Volume: 3.522 `photo_asset`, 10.563 `media_derivative`, 3.521 `media_job`, zero `commercial_history_media`.

| Componente | Chamadas | Tempo acumulado |
| --- | ---: | ---: |
| Consultas SELECT de tenant | 17.599 | 3.087,68 ms de execução de cursor |
| `require_active_owner` | 17.599 | 8.476,72 ms incluindo SQL/ORM |
| SELECT de fotos | 1 | 6,92 ms de cursor |
| SELECT de derivados | 1 | 20,70 ms de cursor |
| SELECT de mídia histórica | 1 | 0,67 ms de cursor |
| `Path.resolve` | 105.612 | 3.290,39 ms |
| `photo_files` de ajuste de prévias | 3.522 | 2.119,44 ms |
| `safe_source_path` | 3.522 | 624,59 ms |
| `safe_derivative_path` | 10.563 | 1.787,76 ms |

Tempos de componentes são aninhados e **não devem ser somados**. Instrumentação adiciona custo, e as medições navegador/função são execuções distintas; seus tempos próximos identificam a etapa dominante, sem constituir benchmark de capacidade.

SHA256 dos arquivos publicados, iguais aos locais após normalização CRLF/LF:

- `backend/app/storage_metrics.py`: `0278339132ceb1a9dd216f631092607ee4c2bc139287bff00462627813fb6612`.
- `backend/app/preview_adjustment/cleanup.py`: `7672cba3f0d50142b3139a720ff672aeeb6b33035caf7dc22456a9217d0a6560`.

## Causa confirmada e contribuições

`admin_validation_summary` em `backend/app/main.py` chama `measure_owned_photo_storage` sincronamente antes de construir a resposta. Esse helper consulta todos os registros próprios, enumera ajustes por foto, resolve caminhos e valida arquivos. Dentro do loop de cada caminho, `require_active_owner` faz `db.get(Tenant, ..., populate_existing=True)`, gerando nova consulta em vez de reaproveitar apenas a identidade já carregada. Houve 17.598 caminhos, mais a validação inicial: 17.599 consultas repetidas de tenant.

O cache de 30s pertence ao helper diferente `measure_photo_storage`. A versão utilizada pelo painel é `measure_owned_photo_storage`, explicitamente sem cache global. Recarregar/navegar novamente, portanto, repete a medição completa. Não é correto ligar o cache global ao painel, pois ele somaria dados entre fotógrafos.

O endpoint também materializa todos os `MediaJob` para agrupar estados em Python e vários conjuntos de IDs apenas para contar. São oportunidades secundárias, sem perfil individual do endpoint inteiro nesta investigação; não são apresentadas como causa principal medida.

## Direção de correção, ainda não implementada

Criar change OpenSpec própria para otimizar a projeção sem alterar sua contagem ou isolamento: eliminar validações SQL redundantes por arquivo com autorização segura no início e antes da resposta, manter filtros/validação de namespace em todos os dados e considerar cache curto **por tenant**, com revalidação de acesso mesmo em cache hit e política de frescor explícita. Contagens/agregações devem ocorrer no banco. Qualquer separação assíncrona do card de armazenamento precisa reconciliar o contrato vigente de chamada única, em vez de introduzir mudança de comportamento sem spec.

Testes futuros precisam cobrir acesso negado/tenant suspenso, cache sem cruzamento entre fotógrafos, limites de paths/symlinks, erro de filesystem sem total parcial e limite de número de queries que não cresça com o número de arquivos. Validar resposta no Chrome após publicação autorizada. Nenhum ganho ou correção foi declarado entregue nesta etapa de diagnóstico.

## Continuidade

JEV foi usado para selecionar dependências e decisões anteriores; os fatos de desempenho vieram do Chrome e do runtime atual. Memória foi consultada somente como contexto e não como prova de desempenho. Nenhuma mudança funcional/refatoração foi feita. O próximo passo é a implementação dessa correção em change própria, caso solicitada pelo proprietário.
