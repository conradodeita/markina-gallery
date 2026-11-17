# Spec Delta

## Purpose

Permitir ao fotógrafo escolher e reservar seu endereço próprio no primeiro acesso verificado, preservando isolamento e distinguindo reserva de infraestrutura pronta.

## ADDED Requirements

### Requirement: Escolha inicial autenticada

O sistema SHALL solicitar a escolha no primeiro acesso após a verificação de e-mail, por aviso no painel e etapa em Configurações, sem adicionar campo obrigatório ao cadastro inicial. O backend MUST derivar tenant e identidade da sessão verificada, sem aceitar tenant_id ou hostname arbitrário do browser. Contas legadas/proprietário SHALL preservar seus endereços e não receber a seleção self-service.

#### Scenario: Fotógrafo novo entra no painel

- **WHEN** a conta signup verificada não possui host
- **THEN** o painel SHALL indicar a escolha pendente e permitir confirmar um prefixo com prévia sob pickyourpic.com.br
- **AND** nenhuma prévia SHALL ser apresentada como reserva já efetivada

### Requirement: Comunicação clara do link da marca

A interface SHALL identificar a escolha como o link ou URL da marca do fotógrafo, sem usar “endereço” isoladamente de modo que possa ser confundido com endereço físico. O aviso do primeiro acesso SHALL compartilhar o alinhamento horizontal do conteúdo administrativo e manter texto e ação legíveis em telas estreitas.

#### Scenario: Fotógrafo entende qual endereço está escolhendo

- **WHEN** o fotógrafo vê o aviso ou a etapa de reserva em Configurações
- **THEN** o sistema SHALL explicar que o nome escolhido formará um link sob pickyourpic.com.br
- **AND** rótulos, prévia, confirmação e estados SHALL usar linguagem de link/URL coerente
- **AND** o aviso SHALL alinhar-se ao conteúdo do painel em desktop e mobile

### Requirement: Reserva atômica e nomes protegidos

O backend SHALL validar prefixo conforme o design, impedir nomes de infraestrutura/existentes e reservar por constraint única global e transação por tenant. Repetição idêntica SHALL ser idempotente e não duplicar auditoria; alterar nome já escolhido SHALL ser recusado nesta entrega, sem liberar ou reatribuir o anterior.

#### Scenario: Dois fotógrafos disputam o mesmo nome

- **WHEN** tenants distintos tentam confirmar o mesmo prefixo normalizado
- **THEN** somente um SHALL obter a reserva
- **AND** o outro SHALL receber indisponibilidade sem dados do titular e sem alteração parcial

### Requirement: Reserva separada de prontidão

Hosts reservados SHALL NOT resolver contexto de cliente nem gerar links públicos. O estado legado SHALL manter comportamento existente. A UI SHALL exibir escolha concluída e preparação pendente sem link navegável até prontidão comprovada. Self-service SHALL NOT promover prontidão, configurar DNS/TLS/proxy ou compartilhar sessão por domínio pai.

#### Scenario: Nome escolhido antes da infraestrutura

- **WHEN** a reserva é persistida com estado reserved
- **THEN** a UI SHALL confirmar a escolha com check e informar preparação pendente
- **AND** resolvedor e geradores de links SHALL recusar esse host sem fallback para markina

### Requirement: Recusa esperada da leitura opcional

A leitura de elegibilidade da etapa de link SHALL continuar negada para PlatformOwner e contas sem onboarding de fotógrafo ativo. O limite global de sessão MUST NOT apresentar essa recusa esperada da leitura GET `/api/admin/onboarding/address` como aviso genérico de sessão/acesso; a API SHALL continuar sem expor dados ou permitir mutação. Respostas 401 e recusas 403 das demais rotas protegidas SHALL manter o tratamento existente.

#### Scenario: Proprietário abre o console da plataforma

- **WHEN** o PlatformOwner autenticado abre uma página administrativa que carrega a consulta opcional do link do fotógrafo
- **THEN** a leitura permanece recusada e nenhum aviso global de “Acesso negado” é exibido por essa recusa esperada
- **AND** o conteúdo do console e o estado da sessão permanecem disponíveis conforme suas permissões
- **AND** uma recusa de outra rota protegida continua produzindo o aviso de acesso negado existente

### Requirement: Continuidade e prova local

A implementação SHALL preservar gates financeiros/WhatsApp, dados e hosts existentes, e SHALL ser validada localmente com tenants sintéticos, sem mutações externas. Promoção operacional de hostname SHALL exigir validação DNS, TLS, proxy e isolamento em etapa própria.

#### Scenario: Proprietário ou host legado

- **WHEN** um tenant existente possui canonical_host sem estado de reserva
- **THEN** resolução e links SHALL manter seu contrato anterior
- **AND** a entrega SHALL NOT mudar o host, credenciais ou dados dessa conta
