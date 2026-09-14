# Revisão do adaptador Web Push — 14/09/2026

## Dependências e licença

Selecionado `pywebpush==2.5.0`, disponível no índice oficial PyPI e instalado no venv local isolado. METADATA da distribuição aponta `https://github.com/web-push-libs/pywebpush`, Python >=3.10, MPL-2.0. Código da biblioteca não foi modificado. Tag 2.5.0 não estava acessível no GitHub durante a consulta; inspeção foi feita no pacote distribuído, não inferida a partir de versão anterior. Dependências novas fixadas em `backend/requirements-push.txt`; Dockerfiles incluem esse arquivo na instalação. Requer cryptography >=47, compatível com 50.0.1 já instalada localmente; build ARM/CI ainda deve validar instalação no destino.

Licenças verificadas no METADATA das distribuições instaladas: pywebpush/py-vapid MPL-2.0; http-ece, attrs, charset-normalizer, urllib3 MIT; aiohttp Apache-2.0 AND MIT; requests, aiosignal, frozenlist, multidict, propcache e yarl Apache-2.0; aiohappyeyeballs PSF-2.0. Os arquivos de licença acompanham os pacotes. Sem modelo/pesos de IA ou uso de criptografia própria.

## Provedores e segurança

Allowlist de hostname: `fcm.googleapis.com`, `updates.push.services.mozilla.com`, subdomínios DNS válidos de `.push.apple.com` e `.notify.windows.com`. HTTPS/443 obrigatório, sem userinfo, fragmento, barra invertida ou caracteres de controle. Não aceitar sufixos semelhantes em domínio de terceiros. Endpoints não são URLs de fetch genérico.

- [Mozilla Autopush](https://mozilla-services.github.io/autopush-rs/http.html): endpoint opaco, Topic e resposta 404/410.
- [Apple Web Push](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers): domínios `*.push.apple.com`, protocolo padrão.
- [Distribuição pywebpush](https://pypi.org/project/pywebpush/): fonte do pacote inspecionado.

Inscrições são Fernet cifradas com chave externa separada de VAPID, contexto de proprietário/geração e fingerprint SHA-256 para unicidade. Segredos não aparecem em estado/API/logs. VAPID usa biblioteca padrão, nunca geração/alteração de chave real pela implementação.

Transporte: DNS em pool limitado de duas resoluções com timeout; rejeita qualquer resposta não global, inclusive resultado misto. Conexão TCP recebe somente endereço numérico previamente validado, sem segunda resolução; TLS/SNI/certificado permanecem validados para o hostname original. Sem proxies de ambiente, redirects ou leitura do corpo remoto. Timeout HTTPS 8 s, TTL máximo 3600 s; Topic estável por evento. Exceções são convertidas em categorias sem endpoint, conteúdo ou credenciais.

## Evidência

`test_web_push.py`: 14 passed. Criptografia/VAPID reais com chaves sintéticas e rede simulada, rejeição de IPs internos, socket fixado sem segunda resolução DNS, redirects não seguidos/corpo não lido, destino interno restrito e payload/configuração inválidos sem chamada externa. Não equivale a entrega real em celular.
