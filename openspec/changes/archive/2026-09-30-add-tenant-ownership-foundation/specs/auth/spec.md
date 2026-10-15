# Spec Delta

## ADDED Requirements

### Requirement: Contexto administrativo vinculado à conta do fotógrafo

O backend SHALL resolver o contexto do fotógrafo a partir da sessão administrativa persistida e de um vínculo ativo com a conta única da instalação, revalidando esse vínculo nas operações protegidas. O sistema MUST preservar os fatores de autenticação existentes e não usar identificadores enviados pelo frontend como autoridade para escolher a conta.

#### Scenario: Administrador legado vinculado
- **WHEN** o administrador atual, migrado com vínculo ativo, conclui senha e TOTP
- **THEN** sua sessão permite a operação na conta única do fotógrafo sem exigir novo cadastro

#### Scenario: Vínculo revogado após login
- **WHEN** o vínculo administrativo é desativado enquanto a sessão ainda é válida
- **THEN** a próxima operação protegida é recusada sem expor recursos da conta

#### Scenario: Tentativa de impor proprietário
- **WHEN** uma requisição administrativa inclui outro identificador de conta na URL, corpo ou cabeçalho
- **THEN** esse identificador não substitui o contexto autorizado e não permite leitura, alteração ou criação para outra conta

#### Scenario: Sessão sem vínculo
- **WHEN** uma sessão administrativa válida não possui vínculo ativo com a conta única
- **THEN** a operação protegida é recusada sem fallback para a primeira conta encontrada
