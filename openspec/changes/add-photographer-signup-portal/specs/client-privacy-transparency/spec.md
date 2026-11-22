## ADDED Requirements

### Requirement: Informação simples e contato para clientes

O sistema SHALL informar clientes, em linguagem simples e adequada à idade, sobre o uso privado das fotos e oferecer um caminho para dúvidas ou denúncias na galeria autenticada. MUST reutilizar somente contato de suporte/privacidade de Termos publicados; se indisponível, orientar o cliente a contatar o fotógrafo pelo canal do convite. A informação MUST NOT bloquear ou atrasar autenticação, navegação, seleção ou compra.

#### Scenario: Galeria autenticada com contato de suporte publicado
- **WHEN** cliente autorizado visualiza a galeria
- **THEN** vê orientação breve sobre privacidade das fotos e um link de contato que usa o endereço publicado do provedor

#### Scenario: Galeria autenticada sem contato de suporte publicado
- **WHEN** não há versão publicada de Termos que forneça o contato
- **THEN** vê orientação para contatar o fotógrafo pelo canal em que recebeu o convite, sem revelar rascunho ou impedir o acesso

### Requirement: Avisos contextuais não substituem controles específicos

O aviso geral de privacidade SHALL coexistir com os controles específicos de autenticação, convite, compra e biometria. MUST NOT introduzir coleta de idade, vínculo obrigatório geral de responsável, ferramenta de supervisão parental, consentimento novo ou gate adicional nesta mudança.

#### Scenario: Cliente menor usa a galeria
- **WHEN** cliente menor conclui o fluxo de acesso vigente
- **THEN** pode navegar, selecionar e comprar conforme as regras atuais, vendo os mesmos avisos contextuais e sem etapa extra

#### Scenario: Busca facial
- **WHEN** cliente inicia ou utiliza busca facial
- **THEN** continuam aplicáveis os avisos, consentimentos e autorizações próprios da busca; o aviso geral não os substitui nem os dispensa

### Requirement: Perfil de cliente sem expurgo automático por inatividade

O sistema SHALL NOT remover automaticamente nome e telefone do perfil operacional de cliente somente por inatividade, ausência de galeria acessível ou conclusão de obrigações correntes. A remoção explícita e auditada permanece sujeita ao controle existente de histórico protegido. Retenção financeira, biométrica, de logs e o processo de direitos do titular são independentes desta regra.

#### Scenario: Cliente sem galeria acessível
- **WHEN** não há galeria acessível ou obrigação corrente para o cliente
- **THEN** o perfil operacional não é apagado automaticamente por esse motivo e os controles de autorização vigentes permanecem aplicáveis

#### Scenario: Exclusão bloqueada por histórico protegido
- **WHEN** uma remoção explícita é solicitada e existe histórico comercial protegido
- **THEN** o sistema preserva o registro protegido e recusa a remoção conforme o fluxo auditado vigente

### Requirement: Histórico comercial sem expurgo automático na primeira versão

Na primeira versão, o sistema SHALL NOT expurgar automaticamente pedidos, pagamentos e compras de clientes por inatividade, ausência de galeria acessível ou encerramento da conta do fotógrafo. Esta regra inicial não estabelece retenção permanente.

#### Scenario: Conta do fotógrafo encerrada
- **WHEN** a conta do fotógrafo é encerrada e não há outra regra de expurgo aplicável aos dados do cliente
- **THEN** pedidos, pagamentos e compras necessários ao histórico comercial permanecem sob os controles de acesso existentes, sem expurgo automático por causa do encerramento

### Requirement: Acesso e prazo do histórico comercial

O sistema SHALL manter somente os dados necessários dos registros comerciais sob os controles de acesso tenant/console existentes. O prazo final e suas exceções MUST permanecer para decisão futura. A edição ou remoção interativa de rascunhos ainda não convertidos em registros históricos segue o fluxo de checkout próprio.

#### Scenario: Consulta de histórico por tenant
- **WHEN** um tenant consulta o histórico comercial
- **THEN** o sistema limita os resultados aos dados autorizados para aquele tenant e mantém os controles de acesso existentes

### Requirement: Retenção provisória de eventos de auditoria

Durante a primeira versão, o sistema SHALL NOT expurgar automaticamente `AuditEvent` ou `PlatformAdminEvent`. A leitura MUST permanecer restrita ao escopo administrativo autorizado, sem acesso por clientes nem leitura cruzada entre tenants. Esta regra é temporária e não estabelece retenção permanente; duração e exceções finais serão definidas futuramente. Ela MUST NOT ser aplicada por inferência a logs técnicos de aplicação, Nginx ou containers nem à telemetria agregada.

#### Scenario: Auditoria global do proprietário
- **WHEN** alguém consulta eventos de `PlatformAdminEvent`
- **THEN** o servidor exige o escopo autorizado do proprietário e não retorna eventos a fotógrafo ou cliente

#### Scenario: Auditoria de tenant
- **WHEN** uma superfície administrativa autorizada consultar `AuditEvent` no escopo de um tenant
- **THEN** o servidor limita a leitura ao tenant autorizado e não expõe os eventos a clientes ou a outros tenants

#### Scenario: Retenção técnica separada
- **WHEN** uma política futura tratar logs técnicos ou telemetria
- **THEN** ela não altera automaticamente a retenção temporária dos eventos de auditoria nem é alterada por esta regra
