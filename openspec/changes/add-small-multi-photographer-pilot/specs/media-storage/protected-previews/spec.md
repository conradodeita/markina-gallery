# Spec Delta

## MODIFIED Requirements

### Requirement: Entrega privada por papel

O sistema SHALL entregar prévias somente após autenticação e autorização da galeria e da pasta para a cliente, por compra confirmada da própria cliente ou pelo papel administrativo. Nenhuma URL persistente de prévia SHALL conceder acesso por posse ou ignorar essas condições.

Nas duas rotas administrativas de prévia, o sistema SHALL validar sessão administrativa vigente, e-mail verificado, vínculo ativo único e conta ativa antes de consultar foto/derivado próprios. A autenticação já realizada pela resolução administrativa do owner MUST NOT ser repetida por aquisição de outra conexão enquanto a sessão da requisição mantém uma conexão ocupada. Requisições concorrentes próprias que cabem no pool sintético SHALL concluir sem aquisição aninhada redundante, mantendo isolamento, auditoria e liberação de conexões. Isto MUST NOT habilitar cache global de autorização, aumentar pool ou alterar segurança da entrega. Prévias SHALL preservar derivados locais autorizados, inclusive autoajustados quando aplicáveis, `Cache-Control: private, no-store` e `X-Content-Type-Options: nosniff`.

#### Scenario: Prévia do cliente
- **WHEN** a cliente autorizada abre uma foto de pasta comum ou atribuída a ela
- **THEN** o sistema entrega somente a prévia protegida daquela foto, sem revelar foto, galeria ou original de terceiros

#### Scenario: Prévia administrativa
- **WHEN** o fotógrafo autenticado abre uma foto para conferência
- **THEN** o sistema entrega prévia administrativa sem marca-d'água, limitada à resolução de conferência, sem download do original

#### Scenario: Acesso indevido
- **WHEN** uma sessão sem atribuição solicita uma prévia de pasta restrita por identificador ou caminho
- **THEN** o sistema nega a solicitação sem revelar a existência da foto, mesmo quando a sessão pode ver outras pastas da mesma galeria

#### Scenario: Prévia de compra confirmada após revogação da pasta
- **WHEN** uma cliente acessa o item do próprio pedido canônico confirmado após perder a atribuição à pasta
- **THEN** o sistema entrega a prévia protegida desse item, mas nega a prévia operacional da pasta e nega o item a outra cliente ou a pedido não confirmado

#### Scenario: Prévias administrativas concorrentes próprias
- **WHEN** dois fotógrafos autenticados consultam suas próprias prévias simultaneamente em fixture com duas conexões e semoverflow
- **THEN** ambas respostas preservam conteúdo/headers/auditoria próprios, sem timeout por autenticação aninhada, e as conexões retornam ao pool após o fim das requisições

#### Scenario: Sessão ou vínculo administrativo perdeu validade
- **WHEN** uma prévia é solicitada com sessão revogada/expirada, papel não administrativo, e-mail não verificado, vínculo inativo ou conta suspensa
- **THEN** a operação é negada antes de entrega de arquivo ou auditoria de visualização, inclusive depois da correção de concorrência

## ADDED Requirements

### Requirement: Isolamento do catálogo de validação das prévias

As fixtures dos testes de concorrência das prévias SHALL construir seu schema a partir de metadata privado e preservar os contratos de constraints e índices efetivos do catálogo ORM usado por outras suítes, sem recriar unicidade global substituída por unicidade scoped nem gerar índices duplicados. DDL PostgreSQL dessas fixtures MUST NOT omitir posteriormente as FKs SQLite responsáveis por recusar foto de pasta/galeria incompatível, mesmo que todos os testes individuais passem em isolamento. A validação SHALL manter banco/queries reais e negativas existentes, sem desabilitar constraints ou aceitar contextos incompatíveis para passar CI.

#### Scenario: DDL de prévias PostgreSQL seguido de constraints SQLite
- **WHEN** o DDL PostgreSQL da fixture de prévias é emitido antes de criar o banco SQLite de uma suíte de isolamento
- **THEN** as inserções de uma foto em pasta de outra galeria ou pasta privada de outra galeria derivada continuam rejeitadas por IntegrityError no SQLite real
