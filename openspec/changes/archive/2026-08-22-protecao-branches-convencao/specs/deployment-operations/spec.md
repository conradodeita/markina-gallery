## MODIFIED Requirements

### Requirement: Repositório com branches protegidas
O repositório SHALL adotar `main` protegida por convenção — alterações somente via pull request com CI verde e revisão —, além de `develop` e branches de funcionalidade, com Conventional Commits documentados. O enforcement técnico de proteção de branch no GitHub permanece pendente de plano compatível (recurso pago em repositórios privados; decisão do proprietário: manter o plano gratuito).

#### Scenario: Alteração direta na main
- **WHEN** alguém tenta alterar a `main` diretamente
- **THEN** o fluxo de trabalho exige pull request com CI verde e revisão antes do merge, conforme a convenção documentada
