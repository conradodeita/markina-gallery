# Spec Delta

## REMOVED Requirements

### Requirement: Propriedade exclusiva da galeria privada derivada

**Reason**: O acervo autorizado passa a ser calculado por galeria, pasta e cliente, sem entidade privada derivada no produto.

**Migration**: Preservar vínculos e históricos legados fora da limpeza autorizada de homologação; novas interações usam a galeria única e a identidade da cliente.

### Requirement: Clonagem privada sem duplicação de mídia

**Reason**: Uma pasta restrita pode ser atribuída a várias clientes sem clonar galeria ou arquivo.

**Migration**: Desativar a criação/clonagem de derivadas e substituir por atribuição explícita de clientes às pastas.

## MODIFIED Requirements

### Requirement: Entrada por link não listado e vínculo individual

O sistema SHALL tratar um link de galeria como não listado e insuficiente para conceder acesso a fotografias. O visitante SHALL informar nome e telefone, concluir OTP e ter vínculo individual autorizado antes de visualizar pastas comuns ou atribuídas. Modo `collective_protected` SHALL preservar a restrição de exposição já aplicável ao acervo coletivo.

#### Scenario: Cliente entra pelo link compartilhado

- **WHEN** uma pessoa abre o link não listado e conclui o OTP com sucesso
- **THEN** o backend confirma seu vínculo antes de apresentar a visão autorizada da mesma galeria, ou um estado de aguardando aprovação

#### Scenario: Evento coletivo protegido

- **WHEN** a galeria representa evento coletivo protegido
- **THEN** o sistema mantém suas exigências próprias de autorização e não apresenta grade anônima

### Requirement: Continuidade segura na troca de telefone

O sistema SHALL permitir ao fotógrafo registrar um novo telefone verificado para a mesma cliente sem transferir pastas atribuídas, seleções ou pedidos a outra pessoa, preservando telefone e nome históricos em registros comerciais concluídos.

#### Scenario: Troca de número da mesma cliente

- **WHEN** o fotógrafo confirma a troca de telefone de uma cliente existente
- **THEN** o novo telefone autenticado recupera as galerias autorizadas e o histórico da mesma identidade, sem alterar snapshots comerciais

### Requirement: Estados privados de descoberta e compra

O sistema SHALL apresentar o estado de cada foto exclusivamente no contexto da cliente autenticada: `nova`, `visualizada mas não comprada` ou `já comprada`. A visualização SHALL ser registrada somente quando a cliente abre a foto ampliada, não pelo carregamento de miniatura.

#### Scenario: Cliente revisita o evento

- **WHEN** uma cliente abre novamente uma galeria com pastas comuns e atribuídas
- **THEN** a interface diferencia para ela as fotos já compradas, ampliadas sem compra e novas, sem exibir estados de outras clientes
