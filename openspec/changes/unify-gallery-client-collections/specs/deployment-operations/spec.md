# Spec Delta

## ADDED Requirements

### Requirement: Limpezas controladas e delimitadas dos dados de teste de homologação

O sistema SHALL fornecer uma operação explícita, inventariada e restrita à homologação para remover galerias, pastas, fotos, clientes, seleções, compras, pedidos, entregas, interações e histórico operacional relacionado, além da mídia e das filas exclusivas desses dados. A operação SHALL preservar conta e sessões administrativas, fatores 2FA, login e instância Evolution, segredos, todas as configurações globais e recursos de outros projetos. Nesta execução autorizada, ela SHALL NOT criar novo backup, executar em produção ou apagar backups preexistentes.

#### Scenario: Inventário anterior

- **WHEN** o operador prepara a limpeza
- **THEN** apresenta contagens e dependências por categoria, raízes de mídia, serviços, porta, subdomínio e itens preservados antes de qualquer mutação

#### Scenario: Execução autorizada

- **WHEN** o proprietário aprova a execução específica após revisar o inventário e o plano de impacto zero
- **THEN** somente os dados de teste e arquivos/filas elegíveis da Markina em homologação são removidos, com registro de resultado e confirmação das contagens zeradas

#### Scenario: Limpeza sem novo backup após deploy validado

- **WHEN** o commit em `develop` contém a sinalização literal de limpeza sem backup e o SHA publicado em homologação corresponde ao SHA explicitamente inventariado
- **THEN** o workflow verifica o SHA e a saúde do serviço, executa a manutenção sem repetir o deploy nem criar backup de pré-deploy e aborta se o código operacional tiver mudado desde o SHA inventariado

#### Scenario: Preservação de credenciais e preferências

- **WHEN** a limpeza termina
- **THEN** a conta admin, 2FA, login/instância Evolution e todas as configurações globais permanecem utilizáveis e com contagens/estado preservados

#### Scenario: Validação temporária concluída

- **WHEN** dados sintéticos são criados após a primeira limpeza para validar a galeria única
- **THEN** esses dados são removidos novamente e a homologação termina com zero galerias, clientes, fotos, seleções e pedidos, mantendo as configurações preservadas

#### Scenario: Ambiente ou inventário divergente

- **WHEN** o ambiente não é homologação ou a operação alcançaria tabela, mídia ou serviço fora da lista aprovada
- **THEN** a operação aborta antes da exclusão
