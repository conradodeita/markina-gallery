# Spec Delta

## ADDED Requirements

### Requirement: Promoção operacional de host reservado

Somente o PlatformOwner SHALL promover o host exato de um tenant de `reserved` para `ready` após revisar os gates DNSSEC, DNS, TLS, proxy, runtime SaaS e isolamento definidos para o ingresso. A operação SHALL exigir estado esperado, intenção idempotente, reautenticação e hash SHA-256 do relatório revisado; SHALL vincular a confirmação ao tenant/host persistidos e auditá-la, sem alterar outros tenants.

#### Scenario: Host aprovado para publicação

- **WHEN** o hostname reservado passa todas as validações e o PlatformOwner confirma a promoção com reautenticação
- **THEN** somente o host do tenant identificado muda para `ready` e a ação fica auditada
- **AND** links canônicos podem usar esse hostname após a transação

#### Scenario: Gate incompleto ou estado divergente

- **WHEN** falta a confirmação/hash, o host/tenant não corresponde à intenção ou o estado atual não é `reserved`
- **THEN** o sistema recusa a promoção e preserva o estado e os dados

#### Scenario: Repetição da mesma intenção

- **WHEN** uma promoção concluída é repetida com o mesmo identificador de intenção e o mesmo tenant/host
- **THEN** o sistema retorna o resultado anterior sem nova mutação nem evento duplicado

### Requirement: Resolução de ingresso por hostname exato

O runtime SHALL associar requisições ao hostname canônico exato de um tenant ativo, exigindo `ready` para hosts SaaS reservados; hosts legados com status nulo SHALL preservar somente seu contrato anterior. Hosts desconhecidos, reservados, inativos, suspensos ou com rótulos adicionais SHALL falhar fechados, sem fallback ao proprietário ou a outro tenant.

#### Scenario: Acesso ao subdomínio ativo

- **WHEN** uma requisição HTTPS chega ao hostname canônico exato de um tenant ativo e pronto
- **THEN** todos os consumidores de identidade e dados usam somente esse tenant e suas URLs canônicas permanecem nesse hostname

#### Scenario: Host desconhecido, reservado ou suspenso

- **WHEN** uma requisição usa hostname não reservado, reservado ainda não pronto, tenant inativo/suspenso ou subdomínio com mais de um rótulo
- **THEN** nenhuma identidade ou dado de tenant é carregado e a conta proprietária não é usada como fallback

#### Scenario: Host legado do proprietário

- **WHEN** a requisição usa o hostname exato previamente configurado para a conta proprietária com estado legado nulo
- **THEN** o acesso mantém o comportamento anterior e não é alterado pela rota wildcard de tenants
