## Why

O Pick-your-Pic está acessível pelo endereço temporário `markina-homolog.duckdns.org`. O proprietário registrou `pickyourpic.com.br` e quer usar `markina.pickyourpic.com.br` como endereço da aplicação, preservando o endereço antigo durante a transição e reservando o domínio raiz para o futuro site institucional.

## What Changes

- Publicar somente o subdomínio `markina.pickyourpic.com.br` para a aplicação atual, com HTTPS válido.
- Manter o hostname DuckDNS e seu proxy/certificado somente durante a validação da migração; depois da revisão do proprietário, retirar a origem adicional e o host virtual antigo da Markina.
- Permitir temporariamente a origem DuckDNS nas verificações de origem de operações sensíveis; usar a nova origem como destino canônico e, ao encerrar a transição, somente ela permanece permitida.
- Não configurar destino ou serviço para `pickyourpic.com.br` neste momento.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: configurar um hostname adicional de homologação com DNS e TLS próprios, preservando o acesso anterior e isolando a mudança à Markina Gallery.
- `auth`: aceitar origens HTTPS explicitamente configuradas para operações sensíveis durante a transição de domínio.

## Impact

- Registro.br: um registro A para `markina.pickyourpic.com.br` apontando para o IP já usado por `markina-homolog.duckdns.org`; nenhum registro raiz, MX ou servidor DNS será substituído.
- Nginx Proxy Manager: um novo host virtual para o subdomínio, usando o alias existente `markina-homolog-nginx` na rede `npm-network` e certificado Let's Encrypt próprio.
- Markina Gallery: variável de origem canônica e lista adicional restrita somente à transição; ao encerrar, remover a variável da allowlist, sem alterar bancos, volumes, credenciais ou serviços de terceiros.
