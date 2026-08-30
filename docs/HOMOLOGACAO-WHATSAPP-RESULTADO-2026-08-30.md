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

O proprietário deve autenticar-se na área administrativa, abrir `Configurações → WhatsApp`, salvar seu número próprio em E.164 e ler o QR ou usar o pairing code no aparelho autorizado. Depois disso devem ser confirmadas identidade coincidente, recuperação após reinício, OTP real sintético, login de cliente e mensagens transacionais. O QR, código de pareamento, telefone completo e credenciais não devem ser registrados neste documento.

## Correção operacional anterior ao pareamento

Na primeira tentativa humana, o número esperado foi salvo, mas o QR não foi exibido. O bloqueio fail-closed ocorreu porque o host já utilizava `APP_ENV=staging` enquanto o bootstrap havia configurado `WHATSAPP_CREDENTIAL_ENV=homolog`. Nenhuma instância ou mensagem foi criada por essa tentativa.

O marcador não secreto foi alinhado para `staging`, preservando todos os segredos e o número esperado. API e worker foram recriados pelo Compose explícito e voltaram saudáveis. A instância dedicada foi criada durante o diagnóstico e permanece sem identidade conectada. A validação interna posterior confirmou ambientes coincidentes e resposta de pareamento com QR e pairing code presentes; seus valores não foram impressos nem persistidos em documentação e nenhuma mensagem foi enviada.
