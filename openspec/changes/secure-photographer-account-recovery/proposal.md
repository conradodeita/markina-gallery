# Proposal

## Why

O encerramento, a eliminação de dados pessoais e a recuperação de acesso foram discutidos juntos, gerando ambiguidade para o proprietário. Perder o e-mail anterior exige atendimento próprio; nome/CPF identificam um cadastro, mas não comprovam sua titularidade.

## What Changes

- Especificar recuperação assistida exclusiva do proprietário, preservando o encerramento, a restauração e a reabertura já implementados.
- Distinguir identificação por nome/CPF, comprovação pelos meios anteriores ou decisão manual do proprietário, verificação do novo e-mail e autorização administrativa.
- Impedir que informar CPF e verificar um e-mail novo seja considerado, por si só, prova suficiente para devolver acesso, inclusive na recuperação após dez anos.
- Decisão substitutiva do proprietário: priorizar meios previamente verificados e vinculados à conta. Quando indisponíveis, permitir recuperação manual exclusiva do proprietário, que verifica a identidade externamente e declara sua decisão no console, com reautenticação, novo e-mail verificado e auditoria. Não exigir nem armazenar documentos, selfies ou evidências externas no SaaS.
- Consolidar mapa de estados, prazos e fontes para o futuro manual, distinguindo implementado localmente, proposto, pendente e produção.
- Separar encerramento do serviço de solicitação de eliminação de dados pessoais; essa separação é de escopo documental nesta change, sem criar expurgo ou alterar retenções.

## Capabilities

### New Capabilities

- `auth/assisted-photographer-recovery`: recuperação de identidade e troca assistida de e-mail com meios anteriores ou declaração manual externa, proprietário reautenticado e auditoria.

### Modified Capabilities

Nenhuma spec principal será sincronizada nesta preparação. A integração com as changes ativas de encerramento/onboarding deverá reconciliar suas regras antes do código, conforme design e tasks.

## Impact

Autenticação, console, interface pública e documentação em implementação local. Reutilizar sessões, desafios, outbox cifrada, recuperação de fatores e auditoria existentes; nenhuma dependência ou mecanismo paralelo foi selecionado. Há código e migration aditiva locais em validação; nenhum segredo operacional, publicação ou operação real. Decisões de retenção e direitos de titulares permanecem separadas; os noventa dias sugeridos não foram aprovados.
