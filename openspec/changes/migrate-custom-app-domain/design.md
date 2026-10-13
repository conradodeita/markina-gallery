## Context

O host Oracle executa a Markina Gallery junto com outros projetos e um Nginx Proxy Manager compartilhado. O proxy da Markina já está conectado à rede externa `npm-network` com alias `markina-homolog-nginx`; o Nginx do projeto encaminha para web/API e publica somente `127.0.0.1:8080` no host. O proxy HTTPS atual recebe `markina-homolog.duckdns.org`. O firewall local está inativo e portas compartilhadas pertencentes a outros projetos existem no host.

O domínio raiz está registrado no Registro.br e usa os servidores DNS automáticos do Registro.br. O painel foi alternado para o modo avançado e informa transição de aproximadamente duas horas antes de liberar a configuração da zona. Nenhuma alteração de registro A foi salva. A resolução pública atual confirma `markina-homolog.duckdns.org` em `132.145.193.169`, enquanto o novo subdomínio ainda não resolve.

## Decisions

### Publicar apenas o subdomínio da aplicação

Criar um registro A para `markina` apontando ao endereço atualmente usado pelo hostname DuckDNS, confirmado por DNS. Manter a zona DNS do Registro.br e não criar redirecionamento para o domínio raiz, registro MX, AAAA ou alteração de nameservers sem necessidade demonstrada.

### Adicionar um virtual host isolado no proxy existente

Adicionar um host no Nginx Proxy Manager para `markina.pickyourpic.com.br`, encaminhando HTTP ao alias existente `markina-homolog-nginx` na porta 80, com redirecionamento HTTPS e certificado Let's Encrypt. O hostname DuckDNS, seu host virtual e seu certificado permanecem intactos. Não reiniciar, reconectar, renomear ou modificar o container compartilhado do Nginx Proxy Manager.

### Preservar operações nos dois endereços

`PUBLIC_APP_ORIGIN` continua sendo a origem HTTPS canônica para links gerados. Adicionar `PUBLIC_APP_ORIGINS` como lista opcional, delimitada e validada de origens HTTPS permitidas por `require_same_origin`. Durante a migração, configurar a origem nova como canônica e autorizar também `https://markina-homolog.duckdns.org`. Nenhum wildcard, origem HTTP ou reflexão do cabeçalho Host é permitido.

### Sequência de publicação e rollback

Implementar e validar o suporte local antes de alterar o servidor. Após aprovação do plano operacional, esperar o Registro.br liberar a zona, criar o registro A, verificar a resolução, adicionar o host e certificado no proxy compartilhado, e só então publicar a configuração/código da Markina por meio do deploy protegido existente. Manter o endereço anterior e registrar o rollback: remover apenas o novo host/certificado e restaurar a origem canônica/configuração anterior da Markina, sem tocar em recursos de terceiros.

## Risks / Trade-offs

- O Registro.br informou transição do modo DNS avançado por cerca de duas horas; até o fim dela não é possível criar/verificar o registro.
- A emissão Let's Encrypt depende de DNS público propagado e acesso externo às portas 80/443 do proxy existente.
- O Nginx Proxy Manager é compartilhado: a mudança deverá adicionar somente um host e certificado, após confirmação do estado atual do proxy e cópia segura da configuração/backup aplicável.
- Atualizar a origem sem permitir explicitamente o domínio antigo bloquearia mutações originadas na aplicação antiga; a allowlist restrita evita isso durante a transição.

## Migration Plan

1. Implementar e testar a configuração restrita de origens e validar OpenSpec.
2. Obter aprovação explícita do inventário, portas, hostname e plano de impacto zero antes de qualquer mudança externa.
3. Após a transição do Registro.br, configurar e verificar somente o A de `markina`.
4. Criar o virtual host/certificado dedicado no proxy e testar TLS, roteamento e healthchecks pelos dois hostnames.
5. Publicar a origem canônica nova mantendo a origem anterior permitida; validar login, cookies, redirecionamentos e operações essenciais.
6. Manter a configuração antiga até validação humana da nova URL; não desativar o DuckDNS nesta mudança.

## Rollback

Se a validação falhar, remover o host virtual/certificado criado para `markina.pickyourpic.com.br`, remover somente o registro A `markina` criado nesta mudança e reverter a origem canônica/allowlist da Markina ao estado anterior. Preservar o hostname DuckDNS e não executar `docker compose down`, prunes, restauração de banco, reinicialização do proxy compartilhado ou mudança em outros recursos.
