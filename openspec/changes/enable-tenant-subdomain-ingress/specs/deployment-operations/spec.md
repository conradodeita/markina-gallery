# Spec Delta

## ADDED Requirements

### Requirement: Wildcard DNS preserva os hosts existentes

O ingresso SHALL usar registro wildcard DNS-only apontado à origem confirmada, após autorização específica e validação de DNSSEC; SHALL preservar a raiz, `markina` e registros explícitos existentes. A mudança SHALL NOT alterar proxy/cache Cloudflare nem recursos de terceiros.

#### Scenario: Wildcard preparado com zona íntegra

- **WHEN** inventário da zona e origem corresponde ao estado público validado e a operação é autorizada
- **THEN** somente o registro wildcard aprovado é criado como DNS-only e os registros exatos permanecem inalterados

#### Scenario: Divergência ou conflito de registro

- **WHEN** DNSSEC, origem, delegação ou inventário diferem do plano aprovado
- **THEN** a operação não cria ou altera registros e informa a divergência

### Requirement: Certificado wildcard e credencial mínima

Um emissor operacional isolado SHALL emitir e renovar o wildcard TLS por DNS-01 usando token limitado às permissões DNS necessárias na zona. A credencial MUST permanecer em cofre operacional protegido, fora do Nginx Proxy Manager e da aplicação; o NPM SHALL receber somente o bundle validado por helper restrito. A credencial MUST NOT aparecer em Git, frontend, banco da aplicação, exportações ou logs.

#### Scenario: Certificado emitido e renovável

- **WHEN** desafio DNS-01 é publicado e validado pela autoridade certificadora
- **THEN** o certificado cobre `*.pickyourpic.com.br`, sua cadeia é confiável e a renovação automatizada passa por ensaio

#### Scenario: Emissor, custódia ou recuperação não comprovados

- **WHEN** emissor, escopo do token, proteção em repouso, recuperação ou compatibilidade do helper não podem ser confirmados
- **THEN** emissão e publicação ficam bloqueadas e nenhuma credencial ampla ou alteração manual não suportada é usada

### Requirement: Rota compartilhada sem interferir em outros hosts

A rota wildcard SHALL encaminhar somente hosts de tenant para o upstream SaaS compatível, preservar `Host` canônico e rotas explícitas existentes, e SHALL NOT alterar serviços ou recursos de outros projetos.

#### Scenario: Host de tenant alcança o runtime compatível

- **WHEN** uma requisição ao subdomínio de tenant chega à rota wildcard validada
- **THEN** ela alcança o upstream SaaS autorizado com o host original e HTTPS válido

#### Scenario: Host explícito ou runtime incompatível

- **WHEN** existe host virtual explícito ou o upstream não comprova compatibilidade SaaS
- **THEN** a rota específica existente mantém precedência e a rota wildcard não é ativada

### Requirement: Operação com inventário e impacto zero

Antes de alterar DNS, certificado ou NPM, o operador SHALL registrar versão/digest disponível, hosts, upstream, portas, redes, credenciais, saúde e rollback; obter autorização humana específica e validar isolamento antes de ativar qualquer tenant.

#### Scenario: Operação aprovada

- **WHEN** inventário, plano limitado, evidência de impacto zero e autorização específica estão presentes
- **THEN** a operação cria somente os recursos aprovados e registra verificações e recuperação

#### Scenario: Aprovação ou evidência ausente

- **WHEN** falta autorização, validação de runtime, evidência de recuperação ou confirmação de que os recursos são exclusivos
- **THEN** DNS, NPM, certificados e estado de tenant permanecem inalterados
