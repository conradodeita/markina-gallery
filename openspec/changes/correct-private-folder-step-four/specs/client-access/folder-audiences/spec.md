# Spec Delta

## MODIFIED Requirements

### Requirement: Aviso somente às destinatárias da pasta

O sistema SHALL preparar o aviso configurado de novas fotos somente para clientes com acesso efetivo à pasta recém-liberada ou atribuída. O aviso SHALL ser idempotente por cliente e rodada; falha de WhatsApp ou push SHALL NOT desfazer a liberação nem divulgar a pasta a outras clientes. Lotes de fotos restritas enviados pela etapa Imagens SHALL usar o mesmo processamento e contrato de destinatários dos lotes enviados pelo acervo individual.

#### Scenario: Pasta restrita liberada

- **WHEN** o fotógrafo libera uma pasta restrita para duas de três clientes vinculadas
- **THEN** somente as duas destinatárias elegíveis podem receber aviso, conforme as configurações globais atuais

#### Scenario: Canal ativado após a liberação

- **WHEN** um canal de notificação é ativado depois que a pasta foi liberada
- **THEN** o sistema não reproduz automaticamente avisos históricos

#### Scenario: Fotos privadas enviadas pela etapa Imagens

- **WHEN** um lote de novas fotos é enviado pela etapa Imagens para uma pasta restrita e o processamento deixa fotos disponíveis
- **THEN** somente as clientes com acesso efetivo recebem o aviso configurado, sujeito à idempotência por cliente e rodada

#### Scenario: Falha parcial em lote da etapa Imagens

- **WHEN** algumas fotos do lote falham no envio e pelo menos uma foto do lote é processada e disponibilizada
- **THEN** o aviso considera somente fotos disponíveis e continua restrito às clientes com acesso efetivo
