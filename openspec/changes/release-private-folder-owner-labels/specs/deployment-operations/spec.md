# Spec Delta

## ADDED Requirements

### Requirement: O classificador de release usa a base de produção verificada
O fluxo de release SHALL comparar o candidato com o SHA saudável de produção registrado e verificado antes de classificar o delta, e SHALL ignorar como release a sincronização que apenas reconcilia o histórico já ativo.

#### Scenario: Sincronização do histórico já publicado
- **WHEN** a `main` recebe o SHA saudável registrado e nenhum runtime novo além desse baseline
- **THEN** o classificador retorna `none` e nenhum preflight mutável ou release de serviços é iniciado

#### Scenario: Delta app descendente da base
- **WHEN** o candidato descende do SHA saudável e altera somente os runtimes API/web declarados no manifesto app
- **THEN** o classificador seleciona `app` para o inventário protegido de API/web

#### Scenario: Delta misto ou sem ancestralidade comprovada
- **WHEN** o candidato mistura escopos, altera worker, migration, Compose ou outro caminho não permitido, ou não descende do SHA saudável
- **THEN** o fluxo não inicia release app; a política app recusa caminhos fora do manifesto e mudanças exclusivamente faciais continuam sujeitas ao fluxo facial independente

### Requirement: Release app valida os blobs de runtime e o schema exatos
O gate app SHALL permitir somente os caminhos API/web fixados no manifesto aprovado e SHALL exigir a revisão de banco esperada pelo inventário atual, sem executar migrations.

#### Scenario: Identificação de responsáveis por pastas privadas
- **WHEN** o delta contém os runtimes revisados para consultar e mostrar responsáveis de pastas privadas e todos os blobs correspondem ao manifesto
- **THEN** o gate permite prosseguir ao inventário somente-leitura limitado a API/web

#### Scenario: Revisão do banco igual ao baseline aprovado
- **WHEN** o servidor registra `20261017_0084`, o candidato não adiciona migration e os demais fatos do inventário correspondem
- **THEN** o preflight pode gerar fingerprint vinculado ao candidato e à revisão `20261017_0084`

#### Scenario: Schema ou conjunto de runtime divergente
- **WHEN** a revisão difere de `20261017_0084`, surge migration, ou qualquer blob/path não corresponde ao manifesto
- **THEN** o gate interrompe o release antes de construir ou recriar containers

### Requirement: Release app mantém OTP e workers fora do escopo
O release comercial SHALL recriar somente `api` e `web` do projeto `markina-gallery` com `--no-deps`, sem recriar workers ou dependências.

#### Scenario: Publicação de API e web
- **WHEN** o fingerprint permanece válido e a aprovação protegida autoriza o SHA exato
- **THEN** somente `api` e `web` são construídos e recriados, sem migration, e o worker OTP permanece em execução

#### Scenario: Alteração de worker ou dependência
- **WHEN** o diff ou comando de release alcançaria worker OTP, worker facial, banco, Redis, Nginx, volume ou Compose
- **THEN** o release é recusado antes de executar comandos mutáveis
