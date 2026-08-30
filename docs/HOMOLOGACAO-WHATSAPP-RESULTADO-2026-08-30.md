# Resultado do deploy WhatsApp em homologação — 2026-08-30

## Publicação protegida

- Autorização explícita recebida depois da apresentação do inventário.
- PR: `#13`.
- SHA integrado e publicado: `49474d5491d89833b1b501d471c6fca98a997b45`.
- GitHub Actions run: `33334772284`.
- Deployment do Environment `homolog`: `6171123289`, estado final `success`.
- Backup lógico exclusivo da Markina criado pela automação antes da troca de SHA.
- Migration confirmada: `20260830_0016 (head)`.

## Verificação de infraestrutura

- `evolution-api`, `evolution-db` e `evolution-redis` saudáveis.
- Limites observados: Evolution 768 MiB/0,75 CPU; PostgreSQL 256 MiB/0,50 CPU; Redis 128 MiB/0,25 CPU.
- Volumes exclusivos presentes: `markina-gallery_evolution-instances`, `markina-gallery_evolution-pgdata` e `markina-gallery_evolution-redisdata`.
- Nenhum dos três serviços possui porta publicada. A única publicação do projeto permanece `127.0.0.1:8080` no Nginx Markina.
- O arquivo `docker/.env.homolog` permaneceu com modo `600`; seus valores não foram impressos, copiados para o Git ou persistidos em logs.

## Verificação funcional anterior ao pareamento

- `https://markina-homolog.duckdns.org/healthz` retornou HTTP 200 e `ok`.
- `https://markina-homolog.duckdns.org/api/health` retornou HTTP 200 e identificou a API saudável.
- `https://markina-homolog.duckdns.org/api/internal/whatsapp/webhook` retornou HTTP 404, confirmando o bloqueio na borda pública.
- A consulta interna sanitizada retornou zero instâncias Evolution.
- O banco Markina retornou zero configurações de canal e zero entregas WhatsApp.
- Nenhum aparelho foi pareado e nenhuma mensagem foi enviada durante o deploy.

## Gate humano restante

O pareamento, a identidade e a recuperação da sessão já foram validados. O proprietário ainda deve solicitar um novo OTP pela própria tela de cliente, confirmar o recebimento no aparelho e consumi-lo no login. Depois desse login, permanece a revisão visual autenticada em desktop e smartphone. O OTP, QR, código de pareamento, telefone completo e credenciais não devem ser registrados neste documento.

## Correção operacional anterior ao pareamento

Na primeira tentativa humana, o número esperado foi salvo, mas o QR não foi exibido. O bloqueio fail-closed ocorreu porque o host já utilizava `APP_ENV=staging` enquanto o bootstrap havia configurado `WHATSAPP_CREDENTIAL_ENV=homolog`. Nenhuma instância ou mensagem foi criada por essa tentativa.

O marcador não secreto foi alinhado para `staging`, preservando todos os segredos e o número esperado. API e worker foram recriados pelo Compose explícito e voltaram saudáveis. A validação interna posterior confirmou ambientes coincidentes e resposta de pareamento com QR e pairing code presentes; seus valores não foram impressos nem persistidos em documentação.

## Pareamento, correção de identidade e recuperação

- O proprietário concluiu o pareamento humano pelo material efêmero exibido no painel.
- A Evolution/Baileys retornou para o mesmo número brasileiro a representação JID legada sem o nono dígito. A comparação literal bloqueou corretamente o envio até que a equivalência estrita fosse especificada e testada.
- O PR `#17` integrou a correção no SHA `19a50db4f292a80468d8b0ed33a44e8e7b01388f`; o run `33337416038` e o deployment `6171668456` terminaram com sucesso.
- A migration permaneceu em `20260830_0016 (head)`; SHA do checkout e `last-healthy.sha` coincidiram com o SHA publicado.
- A consulta sanitizada confirmou provedor `open`, identidade coincidente, canal `ready` e ausência de erro.
- Após reinício controlado somente de `evolution-api`, o serviço voltou `healthy`, recuperou a sessão `open` e o canal retornou `ready`, sem novo pareamento.

## Mensagens sintéticas reais

- Um cliente de homologação e seus objetos de galeria/pagamento foram criados com nomes sintéticos e somente o número próprio autorizado.
- Um OTP terminou `accepted` em uma tentativa, com identificador externo presente e payload cifrado apagado; código e telefone não foram consultados nem registrados.
- As notificações `confirmed`, `refused` e `photographer_reported` terminaram `accepted`/`sent`, cada uma em uma tentativa, com identificador externo e sem erro.
- O destino operacional do fotógrafo foi definido no arquivo seguro do ambiente como o próprio número autorizado, após backup restrito; API e worker foram recriados e voltaram saudáveis.
- A recriação da API invalidou temporariamente o upstream resolvido pelo Nginx e produziu um `502` no primeiro check; somente o Nginx Markina foi recriado, voltou `healthy` e os checks finais retornaram `/healthz` 200, `/api/health` 200 e webhook público 404.
- O recebimento humano do OTP e seu consumo no login permanecem pendentes; estados aceitos pelo provedor não substituem essa confirmação.
