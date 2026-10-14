## ADDED Requirements

### Requirement: Indexação automática em pastas privadas do acervo

Quando o subsistema facial estiver operacionalmente habilitado, o sistema SHALL indexar automaticamente fotos elegíveis em pastas de conteúdo do Acervo do Cliente (`audience_scope = 'selected'`) após os derivados limpos e protegidos estarem prontos. Pastas privadas SHALL NOT herdar nem oferecer pausa local para novos trabalhos faciais. O gate global, autorização por ambiente, criptografia, retenção e controles de consentimento da busca SHALL permanecer aplicáveis.

#### Scenario: Upload privado elegível durante rollout ativo

- **WHEN** derivados protegidos ficam prontos e o rollout global admite indexação
- **THEN** a foto entra no fluxo facial durável sem configuração por pasta

#### Scenario: Gate global fechado

- **WHEN** o rollout global não admite novos trabalhos
- **THEN** a pasta privada não pode habilitar o reconhecimento localmente e o estado informa indisponibilidade

#### Scenario: Retentativa em pasta privada

- **WHEN** o fotógrafo solicita “Refazer reconhecimento”
- **THEN** somente fotos elegíveis daquela pasta são consideradas, respeitando a idempotência e o gate global
