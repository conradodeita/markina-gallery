## Why

O proprietário identificou na página publicada que o seletor SFace/Gemma está visualmente mal disposto. O card usa uma lista sem estilo, texto longo e uma grande área vazia. A ação principal deve ser fácil de localizar e seguir os tokens da página.

## What Changes

- Organizar título, contexto global, motor selecionado e único botão de troca em um card compacto e responsivo.
- Recolher os indicadores de processamento em detalhes expansíveis, com grade legível quando aberta.
- Manter a regra de galerias antigas/incompletas em SFace visível e a informação de calibração acessível.

## Capabilities

### Modified Capabilities

- `privacy-biometric/embedding-engine-evaluation`: apresentação do seletor global já implementado.

## Impact

Somente JSX/CSS do painel de configurações; sem alterações de API, modelo, fila, banco, permissões ou seleção global. O pedido visual constitui aceite deste ajuste de apresentação. Publicação segue as proteções operacionais existentes.
