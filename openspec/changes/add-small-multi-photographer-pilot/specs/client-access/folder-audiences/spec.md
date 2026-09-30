# Spec Delta

## MODIFIED Requirements

### Requirement: Aviso somente às destinatárias da pasta

Os avisos SHALL usar preferências e canais explicitamente vinculados à conta proprietária da galeria. Destinatárias, atribuições e deduplicação SHALL pertencer à mesma conta; canal ausente MUST NOT usar configuração de outra conta. Nas regras abaixo, configurações globais SHALL significar configurações dessa conta.

O sistema SHALL preparar o aviso configurado de novas fotos somente para clientes com acesso efetivo à pasta recém-liberada ou atribuída. O aviso SHALL ser idempotente por cliente e rodada; falha de WhatsApp ou push SHALL NOT desfazer a liberação nem divulgar a pasta a outras clientes.

#### Scenario: Pasta restrita liberada

- **WHEN** o fotógrafo libera uma pasta restrita para duas de três clientes vinculadas
- **THEN** somente as duas destinatárias elegíveis podem receber aviso, conforme as configurações globais atuais

#### Scenario: Canal ativado após a liberação

- **WHEN** um canal de notificação é ativado depois que a pasta foi liberada
- **THEN** o sistema não reproduz automaticamente avisos históricos
