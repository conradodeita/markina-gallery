## Context

Veja `proposal.md` para a motivação. O change `integrate-private-facial-filter` entregou o pipeline funcional e mediu no ARM 419 fotos em 430,467 s, média de 0,973 foto/s, encerrando o lote com 634 processamentos concluídos, 2 falhas terminais, 2.443 faces e zero fila aberta. Essa operação introduziu controles intencionalmente temporários — manifesto de lote, janela, tokens, trailers de commit, monitor e caminhos de pausa/retomada — que não devem virar arquitetura de produção.

O runtime atual já possui embeddings e referências cifrados, jobs duráveis, isolamento por galeria/cliente, retenção, purge, progresso administrativo e retomada de consulta. Produção adiciona riscos diferentes: autorização contínua por escopo, deploy sem desligamentos artificiais, carga simultânea de clientes, prova de representação infantil, observabilidade/SLO e rollback operacional. O host permanece compartilhado com outros projetos e qualquer operação MUST ficar confinada ao projeto `markina-gallery`.

## Goals / Non-Goals

**Goals:**

- transformar o protótipo validado em um runtime de produto sem dependência dos estados de benchmark;
- manter homologação funcionalmente ativa entre deploys para validação da interface;
- iniciar produção fechada, com rollout por allowlist de conta/galeria e expansão auditável;
- separar indexação de acervo, consultas interativas e tarefas de purge/retention para aplicar prioridade e backpressure;
- provar isolamento e admissão durável para pelo menos 100 consultas simultâneas;
- permitir suspensão e rollback sem apagar fotos, pedidos, seleções ou dados de terceiros.

**Non-Goals:**

- ativar produção nesta change sem aprovação humana dos gates listados;
- estimar idade, gênero, emoção, identidade ou valor estético;
- tornar a busca facial condição para publicar ou vender uma galeria;
- criar galeria facial paralela, duplicar cards ou conceder acesso com base em similaridade;
- manter scripts, manifestos ou evidência identificável do benchmark como dependência permanente.

## Decisions

### 1. Separar kill switch de ambiente do escopo de rollout

`FACIAL_PROCESSING_ENABLED` continuará sendo o interruptor técnico do processo, mas não concederá sozinho autorização a qualquer galeria. Um registro persistente e auditável de rollout identificará ambiente, escopo permitido, versões de modelo/calibração/textos, estado `prepared|active|suspended|revoked`, aprovadores, início e eventual término. API e workers repetirão a verificação do kill switch e do escopo no momento de admitir e executar cada job.

Essa separação permite manter homologação ativa sem uma janela de benchmark e impede que ligar uma variável em produção indexe automaticamente todo o banco. A alternativa de usar somente `.env` foi rejeitada porque não oferece rollout granular, histórico nem revogação por galeria.

### 2. Encerrar e remover o caminho operacional do benchmark

Depois da prova agregada de purge, os workflows, modos e testes exclusivos de `activate-private`, `reconcile-private`, `resume-private`, `retry-failed-private`, `monitor` e `close-private` serão removidos do caminho normal. O resultado numérico e a prova de limpeza permanecerão apenas em documentação OpenSpec sem identificadores pessoais, imagens, vetores ou scores.

A lógica de produto comprovadamente reutilizável — fila durável, idempotência, progresso, purge, healthchecks e limites — permanece. A alternativa de manter o script “para uma próxima medição” foi rejeitada porque perpetua dois ciclos de vida concorrentes e aumenta o risco de um trailer temporário controlar deploy futuro.

### 3. Fazer o deploy preservar o estado autorizado

O deploy lerá o estado facial efetivo antes da troca de SHA e aceitará duas combinações coerentes: desligado/worker ausente ou habilitado persistente/worker saudável. No segundo caso, construirá a imagem facial verificada, aplicará migrations aditivas, atualizará API, worker de mídia e workers faciais, validará a mesma configuração efetiva e só então concluirá. Rollback restaurará código e conjunto de workers compatíveis com o estado anterior quando o schema permitir; em qualquer ambiguidade, o kill switch será desligado.

Isso substitui pausas e retomadas por trailer de commit. O default documentado e o primeiro deploy de produção continuam `false`; a persistência descreve o estado autorizado do ambiente, não um default inseguro no repositório.

### 4. Usar rollout persistido por conta/galeria

Será criada uma estrutura aditiva de rollout e aprovação, referenciada por UUID e timestamps UTC, sem segredo ou biometria. Indexação e busca exigirão que a Galeria pública ativa pertença a um escopo de rollout `active`; suspensão bloqueará novas admissões imediatamente e enfileirará purge prioritário quando a finalidade terminar. A indexação administrativa não consulta declaração etária e não depende do gate infantil da cliente.

O painel administrativo exibirá somente estado técnico, cobertura e ação operacional permitida ao fotógrafo. Aprovações jurídicas e de segurança pertencem à configuração de rollout e à auditoria, não a um diálogo repetido para cada foto.

O comando administrativo `Refazer reconhecimento facial` não executará novo upload nem duplicará mídia. Ele reconciliará fotos elegíveis que não possuem job da versão vigente e recolocará na fila todas as falhas atuais da galeria, inclusive em lotes acima de 2.000 itens; jobs concluídos permanecem idempotentes e inalterados.

Em homologação, a ponte remota para essa configuração será um workflow protegido do GitHub separado do deploy. Cada execução SHALL ficar restrita ao projeto Compose `markina-gallery`, a um único UUID público de Galeria pública e ao SHA integral já publicado. A ativação SHALL repetir inventário técnico, criar backup lógico exclusivo da Markina imediatamente antes da mutação, resolver um administrador existente sem registrar seu identificador nos logs e chamar a mesma operação persistente usada pelo produto. Inventário, ativação e suspensão serão modos explícitos; nenhum deles reintroduzirá lote, janela, token ou estado do benchmark encerrado.

### 5. Separar classes de trabalho e priorizar consultas

O banco continuará como fonte durável única, mas o claim aceitará classes de job. Haverá consumidores isolados para `search`, `index` e `maintenance` (`cleanup|purge`), todos sem porta. `search` terá prioridade interativa; `maintenance` terá reserva para que retenção e purge não sofram starvation; `index` usará capacidade remanescente e desacelerará durante picos.

O número de réplicas e limites serão configuráveis por ambiente. Um limite de admissão combinará profundidade da fila, idade do job mais antigo e capacidade efetiva. Requests aceitos sempre serão persistidos antes da resposta; quando o limite for excedido, a API responderá indisponibilidade temporária retentável antes de armazenar a referência.

A alternativa de apenas aumentar a concorrência do worker único foi rejeitada porque mistura latência interativa com backfill e aumenta pico de memória dos modelos sem reserva para limpeza.

### 6. Manter a consulta retomável no backend

A sessão autenticada recuperará a consulta facial mais recente ainda válida por cliente e Galeria pública. O navegador guardará, no máximo, um identificador auxiliar; ele nunca será a fonte de autoridade. Polling usará backoff e cessará em estado terminal, revogação ou expiração. A outbox transacional notificará conclusão sem imagem, resultado, contagem de candidatas ou nova capacidade de acesso.

Os grupos de resultados reutilizarão os mesmos IDs, cards, favoritos, seleção e cotação do acervo. A consulta não cria galeria privada; somente a mutation de seleção existente pode fazê-lo.

### 7. Tratar fluxo infantil na fronteira de consentimento, não no detector

O detector e a indexação não classificam idade. Para a referência enviada pela cliente, produção terá prova não biométrica de representação legal ligada ao cliente, ao fotografado/escopo permitido, à Galeria pública, à versão do texto e à validade. A admissão repete esse vínculo; revogação cancela requests abertos e elimina temporários/candidatas.

`FACIAL_MINOR_SEARCH_ENABLED` será removido como autorização suficiente. Ele poderá permanecer transitoriamente como kill switch adicional durante a migração, sempre subordinado ao registro de representação; depois da compatibilidade, será eliminado.

### 8. Tornar privacidade e retenção verificáveis

Referências continuarão em armazenamento dedicado cifrado e serão eliminadas em estado terminal ou até 15 minutos. Candidatas expiram em até 24 horas. Embeddings pertencem ao escopo de rollout/galeria/foto/modelo e serão purgados por revogação, exclusão, troca incompatível de modelo ou fim da finalidade. Chaves serão distintas por ambiente, versionadas e rotacionáveis sem logar material secreto.

Uma prova agregada contará referências, candidatas e embeddings remanescentes por UUID autorizado. Auditoria registrará evento, escopo, versão, estado, contagens e motivo sanitizado. Direitos de acesso/exclusão operarão sobre esses escopos sem alcançar histórico comercial com base independente.

### 9. Adotar SLOs e rollout em etapas

Antes da produção serão fixados SLOs mensuráveis para disponibilidade de admissão, p95 de consulta sob carga, idade máxima de fila, taxa de falha, prazo de purge e consumo de recursos. A carga de 100 clientes será executada com referências sintéticas ou corpus explicitamente autorizado, verificando isolamento, backpressure e recuperação após restart.

O rollout seguirá `dark` (flag false), `canary` (allowlist mínima), `limited` e `general`. Cada promoção exige janela de observação sem alerta crítico e aprovação registrada. Qualquer regressão volta a etapa anterior ou desliga o kill switch.

## Risks / Trade-offs

- [Modelos ocupam memória significativa por réplica] → medir RSS real por classe de worker, impor limites e escalar somente após inventário do host.
- [Busca prioritária pode atrasar indexação] → mostrar backlog real ao fotógrafo e reservar capacidade mínima configurável para índice.
- [Purge pode sofrer starvation] → consumidor de manutenção reservado e alerta pelo prazo do item mais antigo.
- [Flag ativa sem rollout poderia ampliar escopo] → exigir dupla verificação em admissão e execução; ausência de rollout ativo falha fechada.
- [Representação legal incorreta cria risco alto] → prova não biométrica, expiração, revogação, auditoria e revisão jurídica antes do canary infantil.
- [Remoção precoce das ferramentas de benchmark perde capacidade diagnóstica] → preservar apenas utilitários genéricos de carga/observabilidade; arquivar números e provas no OpenSpec antes da exclusão.
- [Deploy com worker ativo aumenta superfície de rollback] → snapshot do estado anterior, migrations aditivas, healthchecks por processo e desligamento do kill switch quando rollback automático não for seguro.

## Migration Plan

1. Concluir o workflow protegido de fechamento do lote privado e registrar prova agregada de limpeza e healthchecks.
2. Reconciliar `integrate-private-facial-filter`: aceitar a medição 634/636, registrar as duas falhas como amostras tecnicamente inutilizáveis e encerrar as tasks exclusivas do benchmark.
3. Introduzir schema aditivo de rollout/aprovação e gates repetidos em API, indexação e workers, mantendo todos os ambientes desligados por default.
4. Separar claims e processos `search`, `index` e `maintenance`, com limites, prioridade, backpressure e métricas agregadas.
5. Migrar homologação do manifesto temporário para rollout persistente, habilitar `FACIAL_PROCESSING_ENABLED=true`, verificar busca adulta pela interface e manter o fluxo infantil bloqueado até a prova de representação.
6. Remover workflow, scripts, tokens, trailers e estados exclusivos do benchmark; atualizar runbooks, CI e rollback.
7. Implementar e validar representação infantil, direitos, rotação de chaves, alertas e SLOs.
8. Executar testes de segurança, calibração/equidade, retenção e carga simultânea de pelo menos 100 consultas em homologação.
9. Apresentar inventário de produção, topologia, portas/subdomínio, plano de impacto zero, evidências e rollback para aprovação humana.
10. Publicar com flag false, executar smoke sem PII e, somente após aprovação final, ativar o canary por allowlist.

Rollback funcional desliga novas admissões, para os workers pesados e elimina referências temporárias. Rollback de código restaura somente componentes Markina quando a migration aditiva for compatível; caso contrário, mantém o schema e retorna a aplicação ao caminho manual compatível.
