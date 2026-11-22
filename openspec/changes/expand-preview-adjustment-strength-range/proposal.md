# Proposal

## Why

O fotógrafo quer poder ver a prévia sem mistura com a imagem limpa quando o perfil automático do RawTherapee produz um resultado adequado. O limite atual de 75% impede isso.

## What Changes

- Ampliar a faixa de intensidade do ajuste de prévias de 10–75% para 10–100% em pastas e configurações compatíveis.
- Em 100%, mostrar integralmente o resultado ajustado pelo RawTherapee; preservar a exposição em EV como controle separado.
- Manter os valores padrão e os parâmetros do perfil atual.
- Atualizar validações, interface e constraints persistidos por migration aditiva.

## Capabilities

### Added Capabilities

- `media-storage/gallery-preview-adjustment`: permitir intensidade até 100%.

## Impact

Afeta controles administrativos, contratos Pydantic, validação de domínio, constraints das tabelas de configuração e documentação do ajuste de prévias. Os valores existentes permanecem válidos; defaults não mudam. A migration altera apenas os limites das constraints e não reprocessa fotos ou filas.

## Non-goals

- Alterar o perfil `natural.pp3`, exposição automática, brilho, exposição EV ou qualidade do motor.
- Alterar defaults das pastas públicas/privadas, ativação, processamento de fotos, resultados, workers ou segurança de prévias.
- Executar migration ou deploy nesta implementação local.
