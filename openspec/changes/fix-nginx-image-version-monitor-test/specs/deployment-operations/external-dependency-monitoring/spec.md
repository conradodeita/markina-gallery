# Delta: monitoramento da declaração da imagem Nginx

## ADDED Requirements

### Requirement: Componentes externos de runtime permanecem rastreáveis

O monitoramento SHALL validar a imagem declarada pelo serviço `nginx` no Compose sem depender de uma versão específica. A imagem SHALL usar o repositório oficial `nginx`, uma tag numérica explícita no formato `X.Y-alpine` ou `X.Y.Z-alpine`, e uma declaração correspondente no inventário; o ecossistema Dependabot `docker-compose` SHALL continuar cobrindo `/docker`. Tags móveis sem versão, referências inválidas, imagem ausente ou serviço ausente SHALL reprovar a validação.

#### Scenario: Atualização válida de Nginx

- **WHEN** a tag de imagem Nginx é atualizada para outra versão numérica Alpine válida
- **THEN** o teste SHALL aceitar a referência sem exigir a tag anterior e SHALL continuar confirmando inventário e cobertura do Dependabot

#### Scenario: Declaração Nginx ausente ou fora da política

- **WHEN** o serviço ou a imagem Nginx está ausente, usa outro repositório, uma tag móvel, uma tag inválida ou uma variante fora de Alpine
- **THEN** a validação SHALL falhar com erro identificável
