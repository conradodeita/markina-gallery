# Design: correção conjunta de dependências Python

## Contexto

Os alertas são duplicados entre `backend/requirements.txt` e `backend/requirements-push.txt`; o primeiro inclui o segundo com `-r`. As versões operacionais são pins em `requirements-push.txt`, consumidos em runtime pela API, workers e imagens especializadas. Não existe lockfile Python único nem uma versão instalada da Oracle que possa ser confirmada sem acesso operacional, que está fora do escopo.

## Decisões

- Atualizar `aiohttp` para `3.14.4`, corrigindo três GHSA. Seu metadata exige `yarl>=1.25.1,<2`; por isso subir `yarl` de `1.24.5` para `1.25.1`, sem outras atualizações desse pacote.
- Atualizar `multidict` de `6.8.0` para `6.9.1`, corrigindo GHSA-54p9-h82j-f925 e mantendo a major 6. `aiohttp 3.14.4` aceita a faixa 6.x; não usar `multidict 7`.
- Atualizar `urllib3` de `2.7.0` para `2.8.0`, versão corrigida dos três advisories. Validar junto de `requests==2.34.2` e demais pins.
- Manter os demais pins do conjunto Web Push inalterados, salvo se a resolução comprovadamente exigir ajuste adicional.
- Agrupar as quatro linhas num único candidato, porque são requisitos compartilhados pelos mesmos runtimes e o pin de `yarl` é condição de instalação do `aiohttp` corrigido. Não integrar dependências de face/Gemma nem mudar modelo ou configuração operacional.

## Risco e validação

`pywebpush==2.5.0` importa aiohttp e oferece caminho assíncrono (`webpush_async`), mas `backend/app/web_push.py` chama somente `webpush` síncrono e fornece `PushHTTPS`, que conecta por `http.client.HTTPSConnection`; não há chamada da API assíncrona nem servidor aiohttp no código da aplicação. Portanto, os advisories de timeout inicial de servidor e cookie dependem de caminhos ausentes; o advisory de consumo de memória/CPU depende de usar as APIs aiohttp afetadas com dados controláveis. `multidict` é requerido por aiohttp, mas a aplicação não importa seus tipos nem usa as operações de itens do advisory.

`urllib3` é dependência de `requests`, mas o código de aplicação importa `requests.Response` e passa o transporte próprio `PushHTTPS` para `pywebpush`; esse transporte não usa o adaptador de rede de Requests, streaming de respostas ou proxy HTTPS. Assim, os advisories de streaming e proxy não têm caminho de exploração identificado na integração atual. As bibliotecas permanecem instaladas nos runtimes e os alertas justificam corrigir as versões, sem afirmar exploração confirmada nem remover componentes fora do escopo.

Validar a resolução combinada em instalação limpa, `pip check`, suíte backend, e os builds/checks existentes para API, Gemma, runtime de face e workers especializados. Nenhum teste deve iniciar serviços de produção ou acessar Oracle.
