## ADDED Requirements

### Requirement: Diagnósticos operacionais restritos à conta proprietária
O backend SHALL exigir proprietário por UUID, sessão/vínculo válidos e installation_operator para capacidade e observabilidade facial. Propriedade SHALL ser revalidada antes/depois da coleta e na entrega de cache. Capabilities SHALL ocultar acesso de outros administradores. A regra MUST NOT depender de e-mail fixo. Contrato métrico, limites e card SHALL ser preservados.

#### Scenario: Operador antigo não proprietário
- **WHEN** outro administrador possui installation_operator mas não o UUID proprietário
- **THEN** capabilities indicam ausência de acesso e o backend recusa a consulta antes da coleta

#### Scenario: Proprietário troca e-mail
- **WHEN** a conta proprietária troca e verifica o novo e-mail, mantendo UUID, sessão/vínculo e concessão válidos
- **THEN** continua acessando diagnóstico, sem transferir acesso a outra conta que use o e-mail anterior
