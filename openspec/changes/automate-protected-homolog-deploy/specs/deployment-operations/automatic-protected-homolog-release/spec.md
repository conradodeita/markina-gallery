# Delta: Deploy automático em homologação protegida

## ADDED Requirements

### Requirement: Deploy de homologação após CI verde

O workflow SHALL publicar automaticamente em homologação após o sucesso dos checks definidos como dependências do job de deploy e SHALL NOT aguardar aprovação manual por execução no ambiente `homolog`. O ambiente SHALL continuar limitado a branches protegidas, e a proteção de `develop`, seus checks obrigatórios, o inventário, o backup, o preflight, os healthchecks e o escopo exclusivo de `markina-gallery` SHALL permanecer ativos. Esta automação MUST NOT habilitar deploy em produção.

#### Scenario: Push validado em develop

- **WHEN** um merge protegido atualiza `develop` e todos os checks requeridos pelo job de homologação passam
- **THEN** o job inicia automaticamente e executa o fluxo existente de deploy da Markina sem aprovação manual do ambiente

#### Scenario: Check ou preflight falha

- **WHEN** qualquer check obrigatório do deploy falha ou o inventário/preflight detecta divergência
- **THEN** o deploy não inicia ou falha fechado, sem alterar serviços de terceiros

#### Scenario: Worker geral saiu com erro e o alvo contém a correção compatível

- **WHEN** o worker Compose `worker` existente está `exited` com código 1, os logs contêm o erro `value too long for type character varying(192)`, a configuração facial persistida coincide com a do container e o SHA alvo contém a correção limitada da chave do aviso privado
- **THEN** o preflight pode continuar sem iniciar o worker antigo, preserva backup e checks de escritores/migration, recria o worker com a versão alvo e só conclui após o worker e healthchecks Markina ficarem saudáveis

#### Scenario: Worker ausente, estado inesperado ou alvo sem a correção

- **WHEN** o container do worker não existe, seu estado/código de saída diverge do caso de recuperação conhecido, sua configuração difere da persistida ou o SHA alvo não contém a correção
- **THEN** o preflight falha fechado antes de interromper ou substituir serviços

#### Scenario: Branch não protegida ou produção

- **WHEN** o evento não é um push elegível em `develop`
- **THEN** a automação de homologação não publica a versão e os gates de produção permanecem inalterados
