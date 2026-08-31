## MODIFIED Requirements

### Requirement: Liberação de lote para galerias privadas

O sistema SHALL manter a pasta concluída vinculada à Galeria pública de origem e SHALL aplicar seu modo de acesso ao liberar fotos. No modo `standard`, fotos publicadas SHALL poder ser navegadas por clientes autenticadas e vinculadas. No modo `invite_only`, a liberação SHALL alcançar somente clientes associadas e suas referências privadas autorizadas. No modo `collective_protected`, a liberação SHALL permanecer administrativa e SHALL NOT expor grade; somente resultado privado futuro, consentido e aprovado, poderá receber referências. A liberação SHALL preservar o histórico das pastas já vistas pela cliente.

#### Scenario: Lote padrão publicado

- **WHEN** o fotógrafo libera uma pasta concluída em Galeria pública `standard` com navegação habilitada
- **THEN** a cliente autenticada e vinculada vê somente as fotos publicadas e pode iniciar seleção manual

#### Scenario: Lote restrito por convite

- **WHEN** o fotógrafo libera uma pasta concluída em Galeria pública `invite_only`
- **THEN** somente clientes previamente associadas e referências privadas autorizadas podem acessar suas fotos

#### Scenario: Lote coletivo protegido

- **WHEN** o fotógrafo libera administrativamente uma pasta em Galeria pública `collective_protected`
- **THEN** nenhuma cliente recebe a grade e nenhum endpoint de cliente enumera as fotos do lote

#### Scenario: Nova pasta liberada para privada ativa

- **WHEN** o fotógrafo disponibiliza novas referências autorizadas para uma galeria privada ativa
- **THEN** a cliente vê a nova pasta na próxima consulta autorizada sem perder o histórico das pastas já vistas

#### Scenario: Lote concluído

- **WHEN** o fotógrafo libera uma pasta concluída para uma galeria privada ativa
- **THEN** a cliente vê a nova pasta na próxima consulta autorizada e pode revisar somente as fotos liberadas para ela

### Requirement: Exclusão segura de pasta

O sistema SHALL permitir ao fotógrafo excluir diretamente uma pasta vazia ou em preparação sem vínculos privados. Uma pasta liberada SHALL permanecer protegida contra exclusão isolada enquanto referenciada por galeria privada. Durante a exclusão confirmada da Galeria pública, o sistema SHALL remover fotos sem referência privada e pastas que ficarem vazias, mas SHALL conservar, sem duplicação, os ativos e a estrutura mínima ainda utilizados por galerias privadas. A remoção SHALL também preservar a mídia reclassificada como evidência histórica de compra.

#### Scenario: Remoção de preparação abandonada

- **WHEN** o fotógrafo confirma a remoção de uma pasta vazia em preparação
- **THEN** o sistema a remove, registra auditoria e não altera galerias privadas

#### Scenario: Tentativa de exclusão isolada de pasta liberada

- **WHEN** o fotógrafo tenta excluir isoladamente uma pasta ainda usada por galeria privada ativa
- **THEN** o sistema recusa a ação e indica os vínculos que precisam ser preservados

#### Scenario: Remoção em cascata pela Galeria pública

- **WHEN** a exclusão confirmada da Galeria pública alcança uma pasta liberada
- **THEN** o sistema remove a pasta, suas fotos sem referência privada e seus derivados correspondentes, mantendo apenas os ativos ainda necessários às galerias privadas ou ao histórico, sem exigir desvinculação manual prévia

#### Scenario: Pasta contém foto de galeria privada

- **WHEN** a exclusão da Galeria pública encontra uma foto referenciada por galeria privada ativa
- **THEN** o sistema preserva o mesmo arquivo e os derivados necessários à visualização privada, mantém a estrutura mínima de pasta e não duplica a foto

#### Scenario: Foto comprada na pasta removida

- **WHEN** uma pasta a excluir contém foto associada a compra que deve permanecer no histórico
- **THEN** o sistema garante a evidência histórica autorizada antes de apagar o original e os derivados operacionais
