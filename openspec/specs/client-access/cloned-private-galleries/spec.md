# client-access/cloned-private-galleries Specification

## Purpose
Definir entrada segura por link não listado e estados individuais da cliente na galeria única, sem misturar seleção, compras ou histórico entre pessoas. O nome do caminho preserva a referência histórica da capability.

## Requirements

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
