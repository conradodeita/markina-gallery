# Proposta: corrigir alertas de segurança Python

## Why

Quatorze alertas abertos representam sete advisories em dois manifests que compõem a mesma instalação Python. As atualizações isoladas de Dependabot não resolvem o conjunto: `aiohttp 3.14.4` não instala com o pin atual `yarl 1.24.5`, e os mesmos requisitos são consumidos por imagens de runtime diferentes.

## What Changes

- Corrigir as versões vulneráveis de `aiohttp`, `multidict` e `urllib3` com a menor combinação resolvível.
- Atualizar `yarl` somente até a faixa mínima exigida por `aiohttp 3.14.4`, mantendo `multidict` abaixo da versão major 7.
- Validar instalação, resolução e os testes/builds dos runtimes que incluem os requisitos compartilhados.
- Registrar que o diff preparado não atualiza artefatos implantados e que alertas só serão fechados após integração em `main`.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

Nenhuma. É uma atualização de versões e validação de dependências, sem alteração do comportamento especificado do produto.

## Impact

- `backend/requirements-push.txt`, incluído por `backend/requirements.txt` e usado pelas imagens API, face, Gemma, ajuste de prévias e processamento RAW.
- Testes de resolução Python, backend e builds de runtime no GitHub Actions.
- Nenhuma alteração em modelos, serviços Oracle, bancos, migrations, deploy ou publicação.
