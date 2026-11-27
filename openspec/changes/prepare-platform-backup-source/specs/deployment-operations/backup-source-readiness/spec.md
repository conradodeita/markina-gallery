## ADDED Requirements

### Requirement: Preparação protegida e inerte da origem

O operador SHALL preparar somente `source.json` por modo fixo com SHA/pacote atestado, aprovação de ambiente e fingerprint v2 e precondições revalidadas sob lock. SHALL obter a identidade da API ativa e PostgreSQL do inventário aprovado. MUST NOT executar dump, acessar objetos do Drive ou expor dados de configuração.

#### Scenario: Origem confirmada

- **WHEN** o serviço e timer estão inativos, o destino está desativado e as testemunhas coincidem
- **AND** ID, imagem e labels conferem, e API e PostgreSQL observam o mesmo banco, versão, identidade física e schema em transações somente leitura
- **THEN** o operador SHALL publicar somente o arquivo fixo root:root 0400 de forma atômica se ele não existir, ou confirmar sem reescrita um arquivo seguro que representa a mesma origem

#### Scenario: Estado ou configuração divergente

- **WHEN** a origem já existe com valores divergentes, os metadados são inseguros ou qualquer precondição diverge
- **THEN** o operador MUST abortar sem sobrescrever configuração ou prosseguir para cópia, com resultado sanitizado

### Requirement: Precondições verificáveis do vínculo e da execução

A checagem de inércia SHALL identificar propriedades nomeadas e recusar estados inválidos ou duplicados. A API SHALL ser atestada por ID, imagem e labels Compose esperadas. O ensaio SHALL conservar seleção recente, origem preparada, destino desativado e ausência de reconciliação pendente. A execução habilitada SHALL validar e inicializar os subdiretórios fixos `catalog` e `artifacts` sob sua própria raiz de estado.

#### Scenario: A ordem muda ou a unidade diverge

- **WHEN** as mesmas propriedades válidas chegam em ordem diferente
- **THEN** a checagem SHALL produzir o mesmo resultado de inércia
- **AND** uma propriedade ausente, repetida ou estado ativo MUST bloquear a operação
