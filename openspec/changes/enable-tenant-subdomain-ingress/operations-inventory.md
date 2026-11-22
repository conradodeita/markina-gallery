# Inventário operacional somente leitura

Observado em 07/11/2026. Fontes: aba autenticada Cloudflare fornecida pelo proprietário; consultas DNS públicas; SSH autorizado para `ubuntu@132.145.193.169`; metadata Docker, fontes do NPM e consulta SQLite com `mode=ro`. Não foram usados `sudo`, reload, restart, instalação, emissão/renovação de certificado ou escrita de configuração. Valores de credenciais, chaves, cookies e conteúdo de clientes não foram emitidos nem salvos neste relatório.

## Zona e DNSSEC

O painel mostra zona Full, plano Free e **2 registros de 200 disponíveis**. A tabela completa contém:

| Nome | Tipo | Destino | TTL | Proxy |
| --- | --- | --- | --- | --- |
| `pickyourpic.com.br` | A | `132.145.193.169` | 1 hora | DNS-only |
| `markina.pickyourpic.com.br` | A | `132.145.193.169` | 1 hora | DNS-only |

- Nameservers: `kara.ns.cloudflare.com` e `mustafa.ns.cloudflare.com`.
- DNS Settings informa: `Success! pickyourpic.com.br is protected with DNSSEC.` A consulta pública anterior desta execução retornou DS `2371 13 2`.
- Não há wildcard na tabela completa da zona. O nome sintético consultado não recebeu resposta A.
- A inspeção não alterou registros, estado de proxy, DNSSEC ou nameservers.

## Nginx Proxy Manager e origem

| Item | Evidência observada |
| --- | --- |
| Host/contexto remoto | `clearbudget-vnic`, Docker `default` |
| Container | `nginx-proxy-manager`, running; reinício configurado como `unless-stopped`; sem healthcheck Docker |
| Versão do pacote no filesystem do runtime | NPM `2.15.1` |
| Referência da imagem | `jc21/nginx-proxy-manager:latest` — tag móvel; não usar como identidade de rollback |
| Image ID | `sha256:bd94715ff0d6f11047446b2c149d4adb45deaa8e18152b34befb13945b3dbd7b` |
| Repo digest | `jc21/nginx-proxy-manager@sha256:52b2c59994f3d36acfcf70a1626f29734df0ed8c71bacc0269f78b6f939858bb` |
| Arquitetura | Linux/arm64 |
| Portas publicadas | 80, 81 e 443 no host; nenhuma porta foi alterada |
| Redes | `nginx-proxy-manager_default`, `npm-network` e `clearbudget_default`; recursos compartilhados a preservar |
| Dados persistidos | `/home/ubuntu/docker/npm/data` → `/data`; `/home/ubuntu/docker/npm/letsencrypt` → `/etc/letsencrypt`, ambos bind mounts de leitura/escrita existentes |
| Certbot instalado | `5.6.0`, em `/opt/certbot` |
| Plugin Cloudflare instalado | `certbot-dns-cloudflare` e pacote `cloudflare` ausentes no ambiente Certbot consultado |
| Catálogo DNS-01 do NPM | `/app/certbot/dns-plugins.json` oferece Cloudflare/`dns-cloudflare`; pacote e dependência `acme` usam `=={{certbot-version}}`. A instalação dinâmica não foi executada nem comprovada. `CERTBOT_VERSION` não aparece no `Config.Env` Docker consultado; isso não prova o ambiente efetivo do processo Node. |

### Rotas existentes

- `proxy_host` **3**: `markina.pickyourpic.com.br` → HTTP `markina-homolog-nginx:80`, certificado **3**. O nome upstream é alias do container saudável `markina-gallery-nginx-1` na `npm-network`.
- `dead_host` **1**: `pickyourpic.com.br`, HTTPS forçado, certificado **4**; mantém 404 intencional enquanto não há publicação da aplicação raiz.
- `proxy_host` **1** atende `clearbudget.duckdns.org`; permanece fora do escopo de alteração. O registro histórico `proxy_host` 2 está marcado como excluído e não foi modificado.
- `/etc/nginx/conf.d/include/proxy.conf` contém `proxy_set_header Host $host;`.
- Gateway Markina: image ID `sha256:96868d9fa38f469a86d2f25787e43ee9ad330339d30be260aa9f5a338bb03751`, healthy, publicação apenas `127.0.0.1:8080 → 80`.
- Nenhum upstream SaaS com a implementação desta change foi publicado ou validado. Não apontar wildcard ao runtime atual por suposição.

Probes HEAD no Oracle, com validação TLS habilitada:

| Alvo | HTTP | `ssl_verify_result` |
| --- | --- | --- |
| `https://pickyourpic.com.br` | 404 | 0 |
| `https://markina.pickyourpic.com.br` | 200 | 0 |
| `http://127.0.0.1:81` | 200 | Não se aplica — loopback HTTP |

## Custódia da credencial DNS — gate não satisfeito

O fluxo de criação do NPM insere `data` no modelo de certificado (`/app/internal/certificate.js:126`). `meta` é um atributo JSON do modelo, sem transformação criptográfica no código inspecionado (`/app/models/certificate.js:63–77`), e a credencial DNS é consumida de `certificate.meta.dns_provider_credentials`. A omissão desse campo na resposta da API não o cifra no banco.

O arquivo SQLite está em `/home/ubuntu/docker/npm/data/database.sqlite`, **0644 root:root**. Os diretórios ascendentes são atravessáveis por outros usuários (`/home/ubuntu` 0755, `docker` e `npm` 0775, `data` 0755); portanto, as permissões observadas não protegem o banco contra leitura por outros usuários locais. `/data/keys.json` também está 0644; somente sua metadata foi consultada. Criptografia do volume/backup e um ensaio de recuperação segura não foram comprovados.

O código DNS-01 cria o arquivo de credenciais com modo **0600** (`/app/internal/certificate.js:831–833`), mas isso não elimina a cópia em `meta` no SQLite. Os quatro registros de certificado consultados informam `dns_challenge=false` e nenhuma credencial DNS configurada; não foi feita varredura de outros locais do host.

**Consequência:** a task 3.3 continua bloqueada. Não criar, colar ou salvar token Cloudflare no NPM nas condições observadas. A emissão precisa de custódia aprovada e validada antes de qualquer escrita. Uma alternativa candidata é um emissor ACME dedicado, com credencial fora do banco compartilhado do NPM e renovação/instalação do certificado especificadas em change própria; essa alternativa não está aprovada nem implementada. Endurecimento do NPM compartilhado também exige plano próprio de compatibilidade, proteção em repouso e recuperação.

## Emissão e continuidade de atendimento

O NPM desabilita temporariamente configurações de hosts em uso ao criar certificados novos (`certificate.js:140–160`). A seleção inspecionada usa igualdade exata, sem expansão de wildcard (`/app/internal/host.js:206–230`). Neste snapshot, um certificado contendo **somente** `*.pickyourpic.com.br`, emitido antes de criar qualquer rota com esse nome, não corresponde a `markina` nem à raiz. Incluir a raiz na lista de nomes atingiria o `dead_host` existente. Isso é evidência estática, não ensaio de operação sem impacto.

Antes de uma emissão futura autorizada: repetir o inventário dos nomes, comprovar custódia, recuperar/reproduzir configuração em ambiente isolado compatível, medir os efeitos do fluxo NPM e ensaiar renovação. Nenhum consentimento para indisponibilidade foi inferido.

## Recuperação e gates restantes

- Os bind mounts e o digest atual foram identificados; não foi lido conteúdo de backup nem comprovada uma cópia/restauração do NPM. A emissão/rota exige referência de recuperação segura aprovada.
- A task 3.2 recebeu autorização específica e foi concluída em 08/11/2026; o snapshot da zona de 07/11 acima foi sucedido por três registros A, incluindo wildcard DNS-only no mesmo IP. Ver `validation.md` para tabela antes/depois, DNSSEC e probes; o restante deste inventário não foi reconsultado nesta operação DNS.
- A task 3.3 depende da solução de custódia, validação do plugin e ensaio de emissão/renovação, além de autorização operacional.
- A task 3.4 depende de runtime SaaS compatível publicado por release autorizado, recuperação e autorização específica de rota.
- As tasks 4.1, 4.2 e 4.4 dependem dessas etapas. Até lá, não há relatório operacional aprovado nem hash para promover um hostname real a `ready`.
