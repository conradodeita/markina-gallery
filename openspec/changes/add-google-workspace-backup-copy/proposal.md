# Proposal: Cópia externa de backup no Google Workspace

## Why

O backup global e a conexão Google Drive já têm fundamentos locais, mas ainda não existe uma cópia externa verificável do conjunto cifrado. O proprietário definiu Google Workspace como destino e quer concluir um teste com sua conta antes de abrir o SaaS a qualquer tenant, priorizando a segurança dos dados.

## What Changes

- Conectar o fluxo de cópia global ao Google Workspace com a conexão OAuth autorizada e o escopo mais restrito validado. Em 17/11, o proprietário escolheu a mesma conta Workspace para o ensaio e a rotina, conforme D17.
- Enviar somente o arquivo de backup já cifrado; não enviar dumps, configurações ou conteúdo em claro.
- Usar destino dedicado e privado, sem compartilhamento público, com credenciais e chaves fora do código, frontend, logs e tabelas comuns.
- Registrar a origem, o destino, o instante e o estado de upload/verificação/recuperação sem expor conteúdo, tokens ou URLs de sessão.
- Validar localmente com transporte sintético. Antes de abrir o primeiro tenant, testar com a conta do proprietário a leitura de retorno, integridade e restauração em ambiente descartável, e comprovar a cópia recorrente com a conta escolhida.
- Manter suspensão de expurgo e retenção destrutiva até existir cópia sobrevivente comprovada e autorização operacional própria.

## Capabilities

### New Capabilities
- `media-storage/google-workspace-backup-copy`: cópia externa privada, verificação criptográfica por leitura de retorno e gate de recuperação antes da abertura a tenants.

### Modified Capabilities

## Impact

- Backend: integrar o coordenador global existente ao helper OAuth/upload Drive, com retomada, idempotência, leitura de retorno e registro sanitizado.
- Configuração operacional: conexão OAuth autorizada, destino dedicado, custódia protegida e quota observada; o teste pré-abertura usará a conta do proprietário. Nenhum segredo será criado, lido ou configurado nesta proposta.
- Release: o teste real no Workspace será uma etapa pré-abertura, após inventário e autorização operacional específicos. Esta change não autoriza escrita remota, deploy, migration, expurgo nem abertura do SaaS a tenants.
- Não alterar a entrega manual por Google Photos, as prévias locais ou o escopo de recuperação global aprovado. Arquivos de fotos/biometria/WhatsApp e recuperação lógica por tenant permanecem fora desta change.
