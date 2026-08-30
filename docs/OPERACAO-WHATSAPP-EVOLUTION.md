# Operação do WhatsApp com Evolution API

Este runbook cobre o canal transacional da Markina Gallery em homologação. A integração usa Evolution API 2.3.7 com Baileys; ela não é a API oficial da Meta. O canal envia apenas OTP e mensagens transacionais já especificadas. Inbox, chatbot, campanhas e comandos recebidos permanecem fora do escopo.

## Imagens e isolamento verificados

Em 2026-08-30, o registry retornou os seguintes índices multi-arquitetura, fixados no Compose:

- `evoapicloud/evolution-api:v2.3.7@sha256:1bd8afc4a6cf48822e6cf02469aeae7bd35a12a6b616eacd1291926307f4d339`;
- `postgres:15-alpine@sha256:fe0737ba566a2c5b2a28f34433c0a423261900ec17b9bf7ad115e1aae7e57f1b`;
- `redis:7-alpine@sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf`.

Os serviços `evolution-api`, `evolution-db` e `evolution-redis` pertencem ao projeto Compose `markina-gallery`, usam somente a rede interna e não possuem `ports`. Os volumes exclusivos são `markina-gallery_evolution-instances`, `markina-gallery_evolution-pgdata` e `markina-gallery_evolution-redisdata`. O Evolution Manager não é instalado e `/api/internal/` é recusado pelo Nginx público.

## Responsabilidades

### Executor

- inventariar containers, redes, volumes, portas, espaço e consumo antes de qualquer mudança externa;
- validar CI, Compose, migration, backup e healthchecks sem revelar valores de ambiente;
- publicar somente um SHA integrado em `develop`, pelo workflow protegido e após autorização específica;
- confirmar que o canal continua bloqueado até conexão e identidade coincidirem;
- usar somente dados sintéticos nos testes e registrar IDs/estados sanitizados.

### Proprietário

- autorizar explicitamente o deploy da infraestrutura após receber o inventário;
- cadastrar os segredos próprios de homologação por canal seguro;
- informar na tela apenas o número próprio de homologação em E.164;
- ler o QR ou digitar o pairing code no aparelho autorizado;
- confirmar o recebimento das mensagens e revisar os fluxos autenticados.

QR, pairing code, API key, chave OTP e sessão nunca devem aparecer em ticket, commit, log ou captura compartilhada.

## Bootstrap seguro

1. Gere separadamente, no host autorizado, uma API key, um segredo de webhook, uma senha PostgreSQL e uma chave AES-GCM urlsafe-base64 de 32 bytes. Não copie valores entre ambientes.
2. Grave-os somente em `docker/.env.homolog`, com permissão restrita. Configure:
   - `WHATSAPP_CREDENTIAL_ENV` exatamente igual ao `APP_ENV` já usado pelo ambiente; no host de homologação atual ambos são `staging`;
   - `WHATSAPP_PROVIDER=evolution`;
   - `COMPOSE_PROFILES=whatsapp-real`;
   - `WHATSAPP_API_URL=http://evolution-api:8080`;
   - `WHATSAPP_WEBHOOK_URL=http://api:8000/internal/whatsapp/webhook`;
   - um nome de instância exclusivo, além das chaves e senhas sem fallback.
3. Valide sem imprimir a configuração expandida:

   ```sh
   docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml config --quiet
   ```

4. Execute o deploy protegido. A automação inicia banco/cache/Evolution antes de API e worker, sem criar instância conectada ou enviar mensagem.
5. Confirme os healthchecks e consulte `Configurações → WhatsApp`. O estado esperado antes da intervenção humana é `Aguardando pareamento`, `Desconectado` ou `Conectando`, nunca `Canal pronto`.

## Pareamento e reconexão

1. O proprietário salva o número próprio em E.164 na tela. Esse campo declara a identidade esperada; não muda o remetente.
2. O proprietário escolhe `Parear aparelho` e lê o QR/código efêmero no WhatsApp do aparelho autorizado. A tela elimina o material após 60 segundos e permite ocultá-lo antes.
3. O executor escolhe `Atualizar conexão`. Somente estado aberto e número conectado coincidente produzem `Canal pronto`.
4. Em divergência, desconexão ou erro, não reenfileire mensagens manualmente. Corrija a sessão e reconcilie entregas `unknown` antes de aceitar risco explícito de duplicidade.
5. Após reconexão, reinicie de forma controlada apenas `evolution-api`, confirme a identidade e então reinicie `api`/`worker` da Markina, sempre pelo projeto/arquivo explícitos. A sessão deve voltar pelos volumes; se não voltar, os envios permanecem bloqueados e um novo pareamento humano é necessário.

## Backup e verificação de restauração

Antes de atualização ou rotação, faça backup lógico do banco Evolution e archive o volume de sessão em destino exclusivo da Markina, sem remover o original. Registre checksums, permissões, versão da imagem e data UTC. Não inclua os arquivos em Git nem abra seu conteúdo.

A restauração deve ser ensaiada em banco e volumes novos, isolados, nunca sobre o conjunto ativo. Compare integridade e versão antes de planejar uma troca. Substituir o conjunto ativo, apagar volume ou usar `pg_restore --clean` exige autorização humana específica e janela aprovada; este runbook não autoriza essas ações.

## Rotação e comprometimento

### API key ou webhook

1. Bloqueie efeitos externos com `WHATSAPP_PROVIDER=sandbox` em publicação autorizada.
2. Gere valores novos no ambiente seguro, atualize Evolution e Markina na mesma janela e valide o webhook interno.
3. Revogue os valores antigos somente após o canal novo responder e não haver entregas `processing`/`unknown` sem análise.

### Chave OTP

Não rotacione enquanto houver OTP cifrado válido na fila. Aguarde expiração/encerramento, confirme que `encrypted_payload` foi limpo e então publique a nova chave. Perder a chave torna os OTP pendentes indecifráveis; eles devem expirar, nunca ser despejados ou recuperados em texto puro.

### Suspeita de comprometimento

- altere para sandbox pelo fluxo protegido;
- preserve banco, volumes, outbox e logs sanitizados como evidência;
- revogue a sessão no aparelho e rotacione chaves após inventário;
- não apague containers/volumes, não execute prune e não reutilize a instância comprometida;
- trate mensagens `unknown` como possivelmente aceitas e não faça retry cego.

## Atualização fixada e rollback

Toda atualização da Evolution começa em uma nova change OpenSpec, com leitura da release oficial, verificação de digest, compatibilidade de schema, backup e teste local. Nunca use `latest`.

O rollback operacional mais seguro é publicar `WHATSAPP_PROVIDER=sandbox`: isso bloqueia efeitos externos e preserva filas, auditoria, banco e sessão para investigação. Voltar o código usa somente o SHA saudável e o fluxo protegido. Migrations, banco e volumes não são revertidos automaticamente. Nenhum procedimento deste documento autoriza `docker compose down`, prune, remoção de volume, alteração do proxy/DNS/firewall ou recurso de outro projeto.

## Critérios de validação

- `/healthz` e `/api/health` verdes;
- migration Markina no head esperado;
- três serviços Evolution saudáveis e sem porta publicada;
- estado `ready` somente com número conectado mascarado igual ao esperado;
- OTP sintético recebido e consumido uma vez;
- notificações sintéticas com IDs/estados e sem duplicata em falha simulada;
- reinício controlado recupera sessão; se não recuperar, worker bloqueia envio;
- logs e respostas não contêm telefone completo, OTP, QR, mensagem, API key ou sessão.

## Evidência local de recuperação — 2026-08-30

- `docker compose config --quiet` passou com e sem o perfil `whatsapp-real`;
- os três serviços ficaram `healthy`, somente em `markina-gallery_internal` e com `ports=[]` no modelo JSON do Compose;
- a instância sintética `markina-local-recovery-test`, sem identidade conectada, permaneceu consultável após reinício de Evolution, PostgreSQL e Redis;
- API e worker foram executados sobre o banco isolado `markina_gallery_whatsapp_recovery_test`, migrado até `20260830_0016`;
- uma solicitação OTP sintética retornou HTTP 202, terminou `failed` após uma tentativa, sem `external_message_id` e com payload cifrado limpo porque a sessão não estava conectada;
- depois do reinício de API e worker, a mesma entrega continuou presente, no mesmo estado e sem identificador externo;
- os cinco serviços iniciados para o ensaio foram parados explicitamente; volumes e banco sintético foram preservados, sem `down`, prune ou remoção.

O banco de desenvolvimento preexistente não foi usado no ensaio porque estava carimbado com a revision ausente `20260828_0013`. Ele permaneceu intocado; a reconciliação desse histórico é trabalho separado e não deve ser feita por `stamp` ou edição manual sem diagnóstico próprio.
