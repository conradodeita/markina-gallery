# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Diagnóstico exclusivo do administrador da instalação única`
- TO: `### Requirement: Diagnóstico exclusivo do operador autorizado da instalação`

## MODIFIED Requirements

### Requirement: Diagnóstico exclusivo do operador autorizado da instalação

O sistema SHALL fornecer `GET /admin/capacity-observability` somente para sessão administrativa válida com permissão explícita, ativa e revalidada de operação da instalação, independente do vínculo comercial com uma conta de fotógrafo. O diagnóstico SHALL permanecer agregado da instalação e somente leitura mesmo com várias contas. Ser fotógrafo MUST NOT conceder essa permissão. Clientes e fotógrafos comuns SHALL ser recusados antes de iniciar coleta ou entregar cache; a interface SHALL omitir o painel e a ação de cópia para esses usuários. Parâmetros externos de conta SHALL NOT selecionar escopo ou conceder privilégio. Revogação SHALL impedir a próxima consulta e remover dados da interface ao detectar acesso negado. O privilégio de diagnóstico MUST NOT conceder acesso comercial aos acervos de outras contas.

#### Scenario: Administrador autorizado
- **WHEN** o dono com permissão ativa consulta capacidade em instalação com dois fotógrafos
- **THEN** recebe somente o diagnóstico agregado sanitizado da instalação, com os mesmos escopos e limites de evidência

#### Scenario: Cliente ou visitante tenta consultar
- **WHEN** a requisição possui sessão cliente ou sessão administrativa sem permissão explícita de operação
- **THEN** o acesso é negado sem devolver métricas, iniciar coleta ou reutilizar cache, e o painel não aparece para esse usuário

#### Scenario: Contexto revogado ou inválido
- **WHEN** a permissão do operador é revogada após uma coleta anterior
- **THEN** a próxima requisição é recusada mesmo com cache preenchido e o frontend retira o snapshot e a ação de cópia

#### Scenario: Operador tenta acessar acervo alheio
- **WHEN** o operador usa seu privilégio de diagnóstico para solicitar cliente, foto ou pedido de outra conta
- **THEN** a operação exige autorização comercial própria e o privilégio de diagnóstico isoladamente não a concede

#### Scenario: Capability ausente ou consulta indisponível
- **WHEN** a interface ainda não recebeu capability booleana positiva do backend, ou a consulta falha
- **THEN** omite monitor e cópia sem iniciar consulta de métricas

#### Scenario: Retorno à aba e logout
- **WHEN** o operador retorna ao foco ou inicia logout com consulta pendente
- **THEN** a interface invalida os dados anteriores e respostas em voo; no foco revalida capability sem coletar métricas automaticamente, e logout retira o painel

#### Scenario: Cópia após atualização autorizada
- **WHEN** o operador atualiza e copia o relatório
- **THEN** copia exatamente o snapshot corrente sanitizado em `capacity-report/v1`, preservando cache e UTC originais sem acrescentar IDs ou dados de contas

### Requirement: Filas duráveis com cobertura e semântica de espera delimitadas

O diagnóstico SHALL cobrir separadamente mídia, ajuste de prévias, busca facial, indexação facial e manutenção facial. Para cada classe SHALL apresentar contagens de registros aguardando e em processamento, idade da pendência mais antiga quando fundamentada e classificação da aproximação de espera. O sistema SHALL separar trabalhos agendados para o futuro dos aguardando com agendamento vencido quando houver esse dado; itens em processamento MUST NOT integrar a espera de itens ainda aguardando. Uma recuperação possível de lease vencido SHALL ser contagem separada, sem executar recuperação. Quando houver bloqueio por dependência conhecido, a contagem bruta SHALL ser distinguida dos candidatos após esse filtro. A contagem bruta SHALL conservar registros de todas as contas; candidatos e leases recuperáveis SHALL aplicar também o filtro conhecido de conta ativa, sem restringir o diagnóstico à conta comercial do operador. Sem evidência suficiente, elegibilidade ou tempo exato de espera SHALL ficar indisponível.

A cobertura SHALL declarar mensagens/outboxes e outras rotinas não incluídas, sem exibir total geral de todas as filas ou de trabalhos de negócio. Redis de sinalização MUST NOT ser tratado como autoridade de jobs. Nenhuma métrica SHALL afirmar worker ativo, tempo até conclusão, throughput, p95 ou SLO geral a partir desse snapshot.

#### Scenario: Busca agendada e busca em processamento
- **WHEN** há uma busca aguardando com agendamento futuro, outra aguardando com agendamento vencido e uma em processamento
- **THEN** as duas primeiras aparecem em categorias distintas, somente a vencida entra na estimativa dos aguardando aptos pelo agendamento, e a terceira aparece exclusivamente como processamento

#### Scenario: Lease de processamento vencido
- **WHEN** um registro facial em processamento tem lease vencido e agendamento vencido
- **THEN** é contado como processamento recuperável separadamente, sem duplicá-lo na fila aguardando ou alterar lease, tentativas ou estado

#### Scenario: Mídia espera dependência
- **WHEN** um trabalho de mídia aguardando tem análise em estado que bloqueia o claim
- **THEN** entra na contagem bruta e de bloqueados por essa dependência, sem ser apresentado como candidato após o filtro conhecido

#### Scenario: Ajuste sem timestamp de enfileiramento
- **WHEN** a fila de ajuste só dispõe da última atualização do registro
- **THEN** mostra contagem persistida e idade desde atualização como estimativa explícita da espera, mantendo espera exata e elegibilidade completa indisponíveis

#### Scenario: Fila vazia observada
- **WHEN** uma classe foi consultada com sucesso e não tem registros aguardando
- **THEN** mostra contagem zero e ausência de pendência mais antiga, sem converter a ausência em prova de worker saudável

#### Scenario: Conta suspensa conserva fila sem candidatos
- **WHEN** A está suspensa e B está ativa com jobs aguardando ou leases faciais vencidos
- **THEN** os registros de ambas permanecem nas contagens brutas; somente os de conta ativa podem entrar em candidatos ou leases recuperáveis após os filtros conhecidos, sem alterar jobs nem expor IDs de conta
