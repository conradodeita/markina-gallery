## ADDED Requirements

### Requirement: Release web de produção isolado e aprovado
O procedimento de produção SHALL publicar somente o serviço `web` do projeto Compose `markina-gallery`, a partir de um commit identificado e aprovado de `main`, após apresentar ao proprietário o inventário do alvo, portas e subdomínio atendidos, escopo da alteração e plano de impacto e rollback, e aguardar aprovação explícita para aquela execução. O procedimento SHALL verificar a configuração efetivamente usada pelo runtime sem revelar nem alterar valores de segredos, e SHALL parar se o checkout, o projeto Compose, a configuração ou a identidade do alvo não puderem ser confirmados.

#### Scenario: Alvo validado e execução aprovada
- **WHEN** o operador confirma em modo somente-leitura o commit, o projeto Compose, o serviço web ativo, a configuração de runtime, as portas e o subdomínio, e recebe aprovação explícita para a execução apresentada
- **THEN** o procedimento atualiza somente o serviço `web` para o commit aprovado e registra os SHAs anterior e novo, as verificações executadas e o resultado

#### Scenario: Identidade ou configuração divergente
- **WHEN** o rótulo do ambiente, o arquivo montado, o checkout, o serviço ou o projeto detectado diverge do inventário aprovado ou não pode ser verificado
- **THEN** o procedimento interrompe-se antes de alterar recursos e informa a divergência sem imprimir valores de segredos

#### Scenario: Preservação dos demais serviços e dados
- **WHEN** o release ou rollback web é executado
- **THEN** API, banco, Redis, workers, nginx, processamento facial, volumes, redes, proxy compartilhado e configuração de runtime permanecem sem alterações

#### Scenario: Saúde e disponibilidade após o release
- **WHEN** o novo contêiner web é iniciado
- **THEN** o operador verifica o healthcheck e smoke tests no domínio de produção, registra qualquer interrupção observada e inicia rollback apenas do web para o último SHA saudável se as verificações falharem

#### Scenario: Rollback somente do web
- **WHEN** o operador aprovado inicia rollback após falha de saúde ou smoke test
- **THEN** o procedimento restaura somente a versão web anterior registrada, sem restaurar banco, executar migrations ou recriar dependências

#### Scenario: Integração revisada da linha de produção em main
- **WHEN** a versão já implantada é preparada para integração em main
- **THEN** a preparação SHALL conservar os históricos e o contrato de manutenção de main sem acesso remoto, limitando o job operacional de manutenção à ref develop
- **AND** o PR SHALL identificar a versão ativa usada como base e distinguir a diferença de runtime do histórico já implantado, sem autorizar merge ou deploy
