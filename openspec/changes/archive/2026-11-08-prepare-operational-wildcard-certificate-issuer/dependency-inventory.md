# Inventário local de dependências e consumidores

Observado em 08/11/2026 para preparação local. Este inventário fixa candidatos e ligações no código; não declara que foram instalados no servidor.

## Caminhos e consumidores

| Componente | Entrada/consumidor | Fronteira e limite |
| --- | --- | --- |
| `CredentialVault` | `wildcard_operational_service.issuer_once`; testes POSIX e guest sintético | Usa `IntegrationCipher` com contexto operacional e chave do diretório entregue pelo systemd. O app não importa este cofre nem fornece segredo. |
| `CertbotIssuer` | Somente `issuer_once` | Cliente isolado; endpoint Let's Encrypt, SAN wildcard, conta, caminhos, timeout e comandos definidos no código. O token chega por arquivo temporário e nunca é argumento/ambiente. Não houve chamada ACME. |
| `validate_bundle` | `issuer_once` e `wildcard_operational_npm_helper.run` | Confere trust store local, hostname/SAN, cadeia, usos, prazo e par da chave. Sem AIA/OCSP/CRL pela rede. |
| `handle_connection` / socket | Serviço systemd do helper e emissor | SO_PEERCRED, tamanho fixo e JSON estrito. O emissor transmite apenas bundle; não escolhe destino, caminho, comando, hook ou container. |
| `NpmGateway` | `wildcard_operational_service.helper` | `docker` em caminho e host fixos; verifica container, image ID e SHA-256 dos arquivos; usa `docker exec` sem shell. Credenciais/API administrativas NPM não são chamadas. |
| `DurableInstaller` | `wildcard_operational_npm_helper.run`; harnesses sintéticos | Diretório fixo, bundle atômico, fsync, journal de recuperação, `nginx -t`, reload gracioso e probe TLS/HTTP; não expurga versões automaticamente. |
| Units | Templates `scripts/wildcard_issuer/templates/` | Issuer como `pyp-acme`; helper root com grupo de socket restrito. Todos sem seção `[Install]`; nenhum timer é habilitado pelo pacote. |
| Runtime privado do helper | `/data/pyp-wildcard-helper/lib` dentro do NPM aprovado | Extrai wheels conferidas por SHA-256, grava manifesto do conteúdo e verifica cada arquivo antes de importar. Não atualiza nem substitui o runtime Certbot do NPM. |

## Runtime e dependências travadas

| Uso | Runtime e identidade imutável | Pacotes |
| --- | --- | --- |
| Emissor candidato ARM64 | CPython 3.10.19; imagem `python@sha256:5545cc064ff154ca41f886e5e2223ce85f28445d00eb83cd517ce3dd4ba688df`; fonte observada `3.10.19-slim-bookworm` | 30 wheels ARM64 exatas no `scripts/wildcard_issuer/requirements-linux-arm64.lock`, cada uma com SHA-256 e licença em `dependency-manifest.json`; Certbot e plugin Cloudflare 5.6.0; `cryptography` 50.0.0. |
| Helper NPM | CPython 3.13.5 ARM64, runtime preexistente do digest inventariado; biblioteca privada separada | `cryptography` 50.0.0, `cffi` 2.1.1 e `pycparser` 3.12, fixados e hasheados em `helper-dependency-manifest.json` e `requirements-helper-arm64.lock`. |
| Executor compatível | Ubuntu 22.04 ARM64 cloud image SHA-256 `7fc0212296c65f8e20f8e9af89aaab9500ea4ec73cfb245afa0f2b509bb90785`; systemd `249.11-0ubuntu3.23` | Prova QEMU TCG local, sem interface de rede; a versão coincide com a observação read-only do Oracle, mas não substitui teste de configuração/instalação no Oracle. |
| NPM de referência | `jc21/nginx-proxy-manager@sha256:52b2c59994f3d36acfcf70a1626f29734df0ed8c71bacc0269f78b6f939858bb`; Image ID observado `sha256:bd94715ff0d6f11047446b2c149d4adb45deaa8e18152b34befb13945b3dbd7b` | NPM 2.15.1; somente container synthetic `network=none`, sem portas e com dados em tmpfs para os testes. |

## Origem, licença e avisos

- Wheels Python: PyPI; URLs imutáveis a arquivos e SHA-256 registrados nos manifestos. Os dados de licença/projeto vêm do JSON de metadata do PyPI, com URL da metadata gravada por pacote. Nenhum pacote tem licença ausente no manifesto atual; a licença da imagem base Python e dos pacotes Debian é distinta e precisa ser revista se a imagem operacional mudar.
- Avisos: OSV `querybatch` consultado em 08/11/2026 para os 30 nomes/versões do lock retornou zero IDs. `cryptography 48.0.0` foi descartado depois de identificar avisos GHSA/PYSEC; o runtime isolado foi travado em `50.0.0` e a consulta OSV correspondente retornou lista vazia. Isso registra o resultado dessa fonte/data, não garante ausência absoluta de vulnerabilidades nem substitui acompanhamento futuro.
- Certbot, plugin Cloudflare, Python, imagens e manifests são dependências especializadas/operacionais. Não habilitar atualização automática, automerge nem compartilhamento dessas bibliotecas com app/NPM.

## Compatibilidade e limites

`systemd 249` é o alvo porque foi observado no host. `LoadCredential=` foi exercitado em guest Ubuntu 22.04 ARM64 com systemd `249.11-0ubuntu3.23`: três invocações do serviço sintético sobreviveram a um reboot; UID 997 não leu a chave fonte, e o recibo confirmou ausência do token em argv, ambiente, journal e artefatos. A chave fonte chegou como arquivo modo `0400`; `/proc/swaps` estava vazio. `systemd-creds`/`LoadCredentialEncrypted=` não são requisito. Esta prova não comprova a configuração nem a instalação no Oracle; o pacote continua candidato local.

Tags móveis, inclusive `jc21/nginx-proxy-manager:latest`, não são identidade de release. Os IDs/digests acima são fixados para as provas. Não foram atualizados serviços, sistema operacional, runtime do app ou NPM compartilhado.
