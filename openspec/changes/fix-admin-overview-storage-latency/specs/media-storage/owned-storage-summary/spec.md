## ADDED Requirements

### Requirement: Medição própria com autorização atual
A medição SHALL consultar somente mídia do tenant autenticado, validar sua atividade no início e antes da resposta/publicação e manter quantidade constante de consultas SQL de autorização, independente do número de arquivos. Cache SHALL NOT conceder autorização.

#### Scenario: Tenant suspenso com medição memorizada
- **WHEN** uma conta deixa de estar ativa depois de existir uma medição em cache
- **THEN** nova leitura é recusada sem devolver bytes memorizados.

#### Scenario: Suspensão durante coleta
- **WHEN** a revalidação final detecta suspensão
- **THEN** a operação recusa a resposta e não publica a medição no cache.

### Requirement: Cache próprio limitado e temporário
Medições completas SHALL ser memorizadas por no máximo 30s desde o início da coleta, separadas por banco, tenant e raízes, em no máximo 128 entradas. Chamadas da mesma entrada SHALL compartilhar a coleta em andamento sem bloquear globalmente outras contas. Erros SHALL NOT memorizar total parcial. Invalidação explícita SHALL remover também as entradas próprias.

#### Scenario: Dois fotógrafos ou bancos
- **WHEN** consultas usam tenants ou binds distintos, mesmo com UUIDs ou arquivos parecidos
- **THEN** nenhuma medição é reaproveitada entre eles.

#### Scenario: Validade, expiração e raízes
- **WHEN** uma chave válida é repetida antes de 30s
- **THEN** bytes completos podem ser reutilizados com autorização atual; após expiração ou mudança de raiz, uma nova coleta é feita.

### Requirement: Integridade física e contrato do resumo
A medição SHALL manter namespace original e resolvido, confinamento na raiz específica, restrição histórica por item e deduplicação de arquivos. Arquivos ausentes SHALL não contar; erro/arquivo não regular SHALL produzir indisponibilidade sem total parcial. O resumo SHALL preservar seu JSON, contagem atual de fotos, filtros do tenant e carregamento de chamada única, realizando contagens e agrupamentos no banco.

#### Scenario: Caminho indevido ou symlink externo
- **WHEN** uma chave ou resolução escapa da raiz, tenant ou item histórico
- **THEN** nenhum byte desse alvo entra no total e a medição é indisponível.

#### Scenario: Conteúdo autorizado equivalente
- **WHEN** existem originais, derivados e ajustes atuais/legados elegíveis, inclusive referências duplicadas
- **THEN** a medição soma os mesmos arquivos próprios uma única vez, preservando as demais métricas do painel.
