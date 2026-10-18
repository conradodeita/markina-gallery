# Spec Delta

## ADDED Requirements

### Requirement: Reconciliação do baseline coordenado
Quando não houver baseline de aplicação, o procedimento SHALL oferecer inventário somente-leitura e registro inicial aprovado do SHA-base de API e dos IDs reais de API/web, sem recriar contêineres.

#### Scenario: Inventário do baseline inicial
- **WHEN** o operador fornece um SHA-base de API alcançável por `origin/main` e ainda não existe baseline coordenado
- **THEN** o procedimento apresenta os IDs de imagem, configuração, serviços, domínio, portas, impacto e código de aprovação sem alterar o host

#### Scenario: Registro do baseline aprovado
- **WHEN** o proprietário aprova o SHA-base e o inventário exato após confirmar a origem da API
- **THEN** o procedimento registra o SHA-base, cria tags imutáveis para os IDs ativos de API/web e não reinicia nem recria serviços

#### Scenario: Inventário alterado ou origem não comprovada
- **WHEN** o estado ou qualquer ID de imagem muda após inventário, ou a origem da API não pode ser comprovada
- **THEN** o procedimento recusa o registro sem alterar estado ou imagens

### Requirement: Release coordenado de API e frontend
O procedimento de produção SHALL liberar `api` e `web` a partir do mesmo commit aprovado, após inventário atual, validação do SHA, revisão humana e aprovação explícita da execução; o baseline de API e o snapshot real das imagens de ambos os serviços SHALL estar reconciliados.

#### Scenario: Identidade e aprovação do release
- **WHEN** o operador prepara um release coordenado
- **THEN** apresenta o SHA completo de `main`, inventário dos serviços e configurações relevantes, domínio, portas, impacto previsto e plano de rollback para aprovação antes de mutar o host

#### Scenario: Commit ou checkout inelegível
- **WHEN** o checkout está sujo, o SHA não pertence à `main` aprovada, ou há migration ou alteração de configuração Compose incluída
- **THEN** o procedimento recusa a execução e exige uma preparação e aprovação separadas

#### Scenario: Baseline coordenado ausente
- **WHEN** não existe um SHA-base aprovado da API ou um snapshot das imagens reais de API/web aprovado
- **THEN** o procedimento recusa o release sem inferir que os serviços ativos foram construídos do mesmo commit

### Requirement: Escopo restrito de mutação no release coordenado
O release coordenado SHALL construir as imagens-alvo antes da troca e mutar somente os serviços `api` e `web` do projeto Compose `markina-gallery`.

#### Scenario: Preparação bem-sucedida
- **WHEN** ambos os builds terminam com sucesso e o release foi aprovado
- **THEN** somente `api` e `web` são atualizados; banco, Redis, workers, nginx, volumes, redes, proxy, firewall, DNS, certificados, segredos e arquivos de ambiente não são alterados

#### Scenario: Falha antes da troca
- **WHEN** qualquer build-alvo falha
- **THEN** nenhum contêiner em produção é substituído

#### Scenario: Exclusão mútua dos procedimentos
- **WHEN** um release coordenado ou web-only está em andamento
- **THEN** o outro procedimento não inicia até que o primeiro finalize ou seja encerrado de forma registrada

### Requirement: Validação conjunta e registro da versão
O procedimento SHALL validar saúde e rotas HTTPS da API e do frontend e registrar o estado anterior e o resultado dos dois serviços como uma única tentativa de release.

#### Scenario: Release saudável
- **WHEN** ambos os serviços iniciam com as imagens aprovadas
- **THEN** healthchecks da API e web e smoke checks HTTPS configurados passam antes do registro do release como saudável

#### Scenario: Falha de saúde ou smoke check
- **WHEN** qualquer healthcheck ou smoke check falha
- **THEN** o release não é registrado como saudável, a falha e os serviços afetados são registrados, e o operador recebe o estado anterior de cada serviço para eventual rollback aprovado

#### Scenario: Interrupção durante a troca
- **WHEN** API e web estão sendo substituídos pelo Compose
- **THEN** o operador considera que a troca não é atômica e pode causar interrupção breve; o procedimento não declara garantia de zero downtime

### Requirement: Rollback coordenado do release
O procedimento SHALL preservar as imagens anteriormente ativas de `api` e `web` e permitir restaurar esse par registrado mediante aprovação explícita.

#### Scenario: Restauração do estado anterior
- **WHEN** o operador obtém aprovação para rollback após falha ou regressão
- **THEN** restaura as imagens previamente registradas para ambos os serviços e repete as verificações de saúde e HTTPS

#### Scenario: Rollback incompleto
- **WHEN** algum serviço não retorna saudável após restauração
- **THEN** o procedimento registra o serviço e erro remanescentes e não declara o rollback concluído

### Requirement: Compatibilidade do fluxo de release web-only
O procedimento web-only existente SHALL continuar disponível para alterações exclusivas de `web` que não dependam de alterações de API e SHALL respeitar a exclusão mútua com o release coordenado.

#### Scenario: Alteração exclusiva de frontend
- **WHEN** a mudança aprovada afeta somente `web` e é compatível com a API em produção
- **THEN** o operador pode utilizar o procedimento web-only existente

#### Scenario: Alteração que requer API e frontend
- **WHEN** a mudança necessita de suporte novo ou alterado na API
- **THEN** o operador usa o procedimento coordenado, não o procedimento web-only isolado
