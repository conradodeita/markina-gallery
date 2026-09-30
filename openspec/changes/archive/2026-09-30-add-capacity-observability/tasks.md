# Tasks

## 1. Aceite e contrato local

- [x] 1.1 Registrar o aceite humano do recorte e confirmar a base de implementação, guardas de instalação única e diff inicial em `validation.md` desta change; verificar que o escopo autorizado continua sem tuning, schema, ambiente, publicação ou deploy e preservar qualquer trabalho preexistente.
- [x] 1.2 Definir schema tipado fechado do diagnóstico conforme spec/design; testar serialização de observado/calculado/estimado/indisponível, UTC, nulos, valores finitos, enums desconhecidos e proibição de campos sensíveis; documentar campos e unidades em `docs/admin-capacity-diagnostics.md` sem payload real.

## 2. PostgreSQL, pool e lacuna de orçamento

- [x] 2.1 Implementar adaptador somente leitura do pool respondente; testar pool vazio/ocupado, teto finito, overflow ilimitado, size zero, NullPool/tipo desconhecido e introspecção ausente, comprovando ausência de novo engine, alteração de configuração ou abertura para aquecimento; registrar significado e limitação dos valores na documentação.
- [x] 2.2 Implementar agregados PostgreSQL do banco atual/servidor e leitura dos limites/reservas; testar banco atual como subconjunto, conexão da coleta, estados ocultos, reserva não suportada, permissões insuficientes e backend SQLite sem assumir zero; validar em PostgreSQL sintético exclusivo e documentar fontes/escopos sem nomes, SQL em execução ou credenciais na saída.
- [x] 2.3 Implementar resposta de orçamento global indisponível e suas lacunas; testar que topologia versionada, contagem local e diferença positiva para max_connections não geram orçamento, margem ou número de workers; transpor para a documentação o inventário completo e fórmula condicionada do design, conferindo reservas sem dupla contagem e ausência de números operacionais inventados.

## 3. Espera nas cinco classes de fila

- [x] 3.1 Implementar agregação facial por search/index/maintenance a partir de jobs SQL; testar queued vencido/futuro, processing com lease válido/vencido, attempts anteriores, terminais excluídos, vazio, timestamps inconsistentes e categorias sem duplicação; conferir idade calculada e espera estimada com relógio UTC controlado e documentar que Redis não é autoridade nem worker foi observado.
- [x] 3.2 Implementar agregados de mídia com distinção entre queued bruto, bloqueio por análise pending/receiving e candidatos após esse filtro; testar ausência/presença da análise, retries e processing/failed recuperáveis sem reclassificá-los ou invocar worker; documentar o limite da inferência de elegibilidade.
- [x] 3.3 Implementar agregados de ajuste de prévias usando updated_at sem fabricar queued_at; testar fila vazia, queued/processing/terminal, reprocessamento e indisponibilidade da espera exata/eligibilidade completa; documentar estimativa e as filas/outboxes omitidas na cobertura inicial, sem total geral.

## 4. Coleta protegida e endpoint administrativo

- [x] 4.1 Integrar transações curtas somente leitura e limites do coletor; testar no PostgreSQL sintético timeout, lock timeout, rollback/liberação, ausência de configurações locais vazando à próxima sessão, limite de oito SELECTs agregados e cardinalidade constante; inspecionar planos em corpus sintético representativo, registrar duração real sem rotulá-la capacidade de produção e documentar a limitação de aquisição do pool.
- [x] 4.2 Implementar cache em memória por até 30 segundos, exclusão mútua por processo e falha parcial por seção; testar atualização de UTC somente em coleta real, cache expirado, chamadas concorrentes, coleta ocupada, perda do cache após reinício e erro isolado sem zerar dados; registrar evidência e o comportamento de atualização na documentação.
- [x] 4.3 Expor GET administrativo com autorização antes da coleta/cache e `Cache-Control: no-store`; testar admin válido, anônimo, cliente, sessão revogada, vínculo ausente/revogado, conta suspensa/ausente/múltipla e tentativa de impor tenant, inclusive cache previamente preenchido; comprovar que acesso negado não inicia coleta e que falha de autenticação por infraestrutura não retorna snapshot.
- [x] 4.4 Validar sanitização e ausência de efeitos: injetar sentinelas de nome/telefone/token/SQL/caminho/biometria nos registros e erros, inspecionar resposta e logs, comparar estados/leases/tentativas/configurações antes e depois e testar que nenhum provider, claim, notifier, filesystem ou Redis é acionado; registrar resultados em `validation.md` e preservar métricas/allowlists faciais existentes.

## 5. Apresentação na Visão geral

- [x] 5.1 Implementar seção inicialmente recolhida na `/admin` com componentes existentes, consulta sob demanda e atualização manual; testar que fechada não consulta, não duplica requisição em andamento, não faz polling, cancela ao desmontar e exibe UTC, escopo, evidência e cobertura sem controles de tuning; documentar caminho de acesso e comportamento esperado.
- [x] 5.2 Cobrir na UI dados completos/parciais, zero observado, null indisponível, espera estimada, cache, falha de rede e perda de autorização com remoção do snapshot; verificar acessibilidade por teclado, carregamento/erro isolados do restante do painel e apresentação em viewport móvel por testes de componentes e validação visual local sintética; registrar qualquer limitação visual, sem acessar OTP/servidor real nesta implementação local.

## 6. Integração e entrega revisável

- [x] 6.1 Executar regressões de observabilidade facial e autorização/ownership, testes novos de diagnóstico, lint backend/frontend, typecheck, testes frontend e build aplicáveis; validar a change e o conjunto OpenSpec em modo strict, investigar falhas relacionadas e registrar comandos/ambiente/resultados em `validation.md`, sem declarar PostgreSQL validado se apenas SQLite foi executado.
- [x] 6.2 Revisar diff e documentação de ponta a ponta, conferindo contrato anterior do resumo/facial, preservação de arquivos preexistentes, ausência de código/configuração fora do recorte e nenhuma tarefa marcada sem evidência; entregar relatório com limitações e roteiro de aceite. A revisão humana autorizou sync/archive em 2026-09-30; publicação/deploy permanecem sujeitos a autorização própria com inventário, portas/subdomínio e impacto zero.

## Execution Notes

Estado desta entrega: implementação local após aceite humano; 16/16 tasks concluídas. As tasks 2.2 e 4.1 foram validadas num PostgreSQL 17 sintético exclusivo em `127.0.0.1:55469`, com armazenamento efêmero, corpus agregado representativo, cinco SELECTs, planos válidos, timeouts, rollback/liberação, ausência de vazamento de configurações e permissão insuficiente sanitizada. A rodada final medida levou 0,110 segundo, somente como evidência do corpus local, sem valor de capacidade ou SLO. A task 5.2 foi validada em prévia sintética isolada, em desktop e viewport móvel de 390×844, sem OTP nem consulta ao endpoint real; a inspeção encontrou e corrigiu a compressão dos rótulos do pool no breakpoint móvel. Inventário remoto incompleto não impede declarar orçamento global indisponível, mas impede preenchê-lo. Aprovação de SLOs e esquema métrico amplo, estudos B05/B06/B11 e orçamento global são dependências do P0.3 completo, fora das tasks desta change. P0.2/fairness, quotas e múltiplos fotógrafos continuam excluídos. Após revisão humana explícita, os sete requisitos e 23 cenários foram sincronizados na spec consolidada e a change foi arquivada em `2026-09-30-add-capacity-observability`.

Cada task deve ser concluída e validada antes da próxima dependente; registrar bloqueios e avançar somente nas independentes seguras. Não usar aprovação/resultado de CI, deploy ou limpeza de outro chat como autorização operacional desta change.

## Planning Validation

Antes do arquivamento, `npx --yes @fission-ai/openspec validate add-capacity-observability --strict --json` passou (1/1). Depois da sincronização e do arquivamento, `npx --yes @fission-ai/openspec validate --all --strict --json` passou (73/73, zero falhas). Essas validações não comprovam métrica ou capacidade de runtime além das evidências sintéticas delimitadas em `validation.md`.
