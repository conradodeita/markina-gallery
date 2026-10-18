## ADDED Requirements

### Requirement: Runtime de Vendas e pagamentos tem allowlist API/web exata
O verificador de release API/web SHALL reconhecer somente os arquivos de runtime de pagamentos e exportação enumerados no manifesto, com hashes de blob correspondentes ao candidato.

#### Scenario: Candidato revisado de pagamentos
- **WHEN** o candidato altera os runtimes enumerados e o manifesto contém seus blobs exatos
- **THEN** o classificador aceita o escopo API/web, mantendo o restante da allowlist fechado

#### Scenario: Runtime fora da lista
- **WHEN** o candidato altera um caminho de runtime não enumerado
- **THEN** o verificador recusa o release por divergência de escopo ou blob

### Requirement: Remoção da página de Estatísticas é uma exceção exata do escopo API/web
O verificador SHALL tratar como aposentados somente a página e o teste antigos de Estatísticas, sem listá-los como runtimes ativos.

#### Scenario: Remoção autorizada da rota antiga
- **WHEN** o candidato remove `frontend/app/admin/statistics/page.tsx` e `frontend/app/admin/statistics/page.test.tsx`
- **THEN** o classificador aceita somente essas duas remoções exatas

#### Scenario: Outro caminho de Estatísticas
- **WHEN** o candidato altera qualquer outro caminho sob `frontend/app/admin/statistics/`
- **THEN** o verificador recusa o release por caminho fora do escopo

### Requirement: Sincronizar hashes não aprova uma publicação
Atualizar hashes de runtime MUST NOT alterar baseline de produção, revisão do banco ou estados dos gates operacionais. Um release ainda requer inventário somente-leitura e aprovação protegida do fingerprint e SHA exatos.

#### Scenario: Manifestos sincronizados sem inventário
- **WHEN** os hashes do candidato são sincronizados, sem inventário aprovado
- **THEN** o fluxo não publica nem declara release autorizado
