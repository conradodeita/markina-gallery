# Matriz de viabilidade — 07/11/2026

| Componente | Origem/versão/licença | Consumidor e limite |
| --- | --- | --- |
| NPM | 2.15.1, MIT; índice OCI `sha256:52b2c59994f3d36acfcf70a1626f29734df0ed8c71bacc0269f78b6f939858bb`, manifest ARM64 `sha256:a36f72b9b4a44b7ca64ecdb80d903a635f9fe80bc01a1d68e0d4d4bd1e01b0d5` | Consumidor de certificado; fonte do runtime já inventariada. Upload nativo rejeitado para esta solução por persistência de material em meta. |
| Certbot/DNS Cloudflare | Candidato 5.6.0, Apache-2.0; documentação oficial do plugin | Emissor dedicado futuro; nenhum cliente real é invocado pelo protótipo. Token mínimo Zone:DNS:Edit somente na zona selecionada; nunca Global API Key. Arquivo temporário 0600; Certbot registra caminho, não conteúdo. Instalação/plugin e transitivos exigem validação própria antes de operação. |
| IntegrationCipher | Código existente, AES-GCM/cryptography já declarado pelo projeto | Reutilizar contexto explícito e exclusivo `wildcard-dns-lab-v1`, sem ler/escrever env, sem reutilizar keyring operacional. Chave sintética injetada em memória; não persistir chave junto ao ciphertext. |
| systemd credentials | Candidato loader Linux, documentação systemd 255/atual; LGPL-2.1-or-later no projeto upstream | Referência de implantação, não executado nem presumido disponível no Windows/NPM. O adaptador local não equivale à prova do loader real. |

## Fontes primárias consultadas

- [Template NPM 2.15.1](https://raw.githubusercontent.com/NginxProxyManager/nginx-proxy-manager/v2.15.1/backend/templates/proxy_host.conf): `advanced_config` é emitido dentro do bloco do host; candidato a referências fixas de arquivos SSL sem certificado nativo. Isso ainda exige ensaio de geração e TLS no NPM.
- [Configuração avançada NPM](https://nginxproxymanager.com/advanced-config/): include global `server_proxy.conf` abrange todos os hosts e por isso é rejeitado para esta integração; não confundir Docker file secrets com cifragem do meta DNS.
- [Credenciais Certbot Cloudflare](https://certbot-dns-cloudflare.readthedocs.io/en/stable/): permissões e arquivo de credencial; o cliente real não será executado neste laboratório.
- [systemd credentials](https://github.com/systemd/systemd-stable/blob/v255-stable/docs/CREDENTIALS.md): materialização e loader cifrado; suporte efetivo precisa de ensaio específico antes de operação.
- Licenças: [NPM MIT](https://raw.githubusercontent.com/NginxProxyManager/nginx-proxy-manager/v2.15.1/LICENSE), [Certbot Apache-2.0](https://raw.githubusercontent.com/certbot/certbot/v5.6.0/LICENSE.txt), [systemd LGPL](https://raw.githubusercontent.com/systemd/systemd/v255/LICENSE.LGPL2.1).

## Seleção local e fronteiras

Selecionado para prova: cofre sintético cifrado com referência UUID e expiração autenticada, materialização efêmera POSIX restrita, transporte sintético e instalador com destino fixado em diretório marcado de laboratório. O NPM recebe somente arquivos de certificado/chave e configuração contendo caminhos, nunca token. Um responsável externo pela renovação; não criar registro LE nativo para esse wildcard. O emissor não recebe shell, socket Docker ou cliente API administrativo NPM. O runner de laboratório atua como operador e liga callbacks de teste/reload/probe fixos; isso não constitui helper privilegiado aprovado para produção.

O candidato per-host passou no NPM 2.15.1 ARM64 do digest inventariado: TLS real local, renovação, replay e retorno, com tabela de certificados vazia. O consumidor NPM não recebeu/montou o cofre do teste de custódia. Dezesseis probes TLS sem retry dos hosts sintéticos raiz/markina passaram durante as trocas. Ver `validation.md`; essa amostra não prova disponibilidade sob carga nem viabilidade do helper/store operacionais. Não usar include global, SQL manual em produção ou upload de chave como fallback.

Inventário local: Docker `desktop-linux`, cinco containers preexistentes preservados, imagem NPM ainda não presente antes desta execução; C: com aproximadamente 22,5 GB livres. Pull do digest oficial limitado ao laboratório; sem prune, sem alterar redes/containers preexistentes. Laboratório executado com `network=none`, sem portas publicadas e com dados sintéticos em tmpfs; container e JWT sintético temporário removidos após a prova, imagem/cache preservados.

Criticidade: NPM/TLS e custódia são componentes críticos. O laboratório consumiu Python 3.13.5 e cryptography 48.0.0 já presentes no digest (metadata de licença `Apache-2.0 OR BSD-3-Clause` para cryptography); não promove essas versões ao runtime da aplicação nem atualiza o proxy compartilhado. Riscos de cadeia pública, compatibilidade do helper, segregação de identidades, recuperação da chave e renovação real permanecem gates explícitos do runbook.
