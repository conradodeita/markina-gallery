# Delta de especificação: Operações de implantação

## ADDED Requirements

### Requirement: Exceções precisas na varredura histórica de segredos

Uma exceção de falso positivo na varredura de segredos SHALL identificar um único achado por impressão digital completa e SHALL registrar a evidência de que o valor é sintético ou não secreto. Exceções MUST NOT desativar uma regra, arquivo, diretório ou padrão amplo.

#### Scenario: Marcador de redação detectado como chave

- **WHEN** o Gitleaks sinaliza um marcador textual de redação em um artefato histórico
- **THEN** o responsável verifica o conteúdo e a origem sem reproduzir valores de credenciais nos relatórios
- **AND** uma exceção, se necessária, corresponde apenas à impressão digital completa do achado verificado
- **AND** a varredura histórica continua ativa para todos os demais conteúdos
