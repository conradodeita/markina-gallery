# Operação das notificações de pagamento

## Escopo e separação financeira

A cliente pode informar que realizou o PIX, mas essa comunicação não confirma
o pagamento. Somente o fotógrafo autenticado decide entre **Confirmar
pagamento** e **Pagamento não localizado** no painel **Pagamentos**. A primeira
decisão fica preservada e novas requisições não repetem a decisão nem a
mensagem.

As notificações são transacionais. O fluxo não envia campanhas, comprovantes,
imagens, links públicos, dados bancários ou credenciais.

## Sandbox local

O padrão é `WHATSAPP_PROVIDER=sandbox`. Nesse modo o worker percorre a caixa de
saída e valida destinatário, template, idempotência e tentativas, mas não faz
chamadas externas. Use somente clientes, telefones e pedidos sintéticos.

As variáveis abaixo pertencem ao arquivo seguro de cada ambiente e nunca devem
receber valores reais em `.env.example`, issues, logs ou commits:

```dotenv
WHATSAPP_PROVIDER=sandbox
WHATSAPP_CREDENTIAL_ENV=development
WHATSAPP_API_URL=
WHATSAPP_API_KEY=
WHATSAPP_INSTANCE=
WHATSAPP_PHOTOGRAPHER_PHONE_E164=
WHATSAPP_MAX_ATTEMPTS=3
WHATSAPP_TIMEOUT_SECONDS=10
```

- `WHATSAPP_CREDENTIAL_ENV` deve ser exatamente igual a `APP_ENV`; o processo
  recusa credenciais rotuladas para outro ambiente.
- `WHATSAPP_PHOTOGRAPHER_PHONE_E164` deve conter somente o telefone do
  fotógrafo previamente verificado, em E.164.
- `WHATSAPP_MAX_ATTEMPTS` aceita de 1 a 10 tentativas.
- O worker e a API recebem as mesmas variáveis pelo Compose, mas apenas o
  worker entrega notificações transacionais da caixa de saída.

## Ativação do Evolution API

A ativação externa exige inventário de impacto zero e autorização explícita.
Homologação e produção devem usar instâncias, chaves e arquivos de ambiente
distintos.

1. Confirme o ambiente, o telefone verificado do fotógrafo e a instância
   Evolution dedicada à Markina.
2. Guarde URL, chave e instância somente em `docker/.env.homolog` ou
   `docker/.env.prod`, com permissões restritas.
3. Defina `WHATSAPP_PROVIDER=evolution` e faça
   `WHATSAPP_CREDENTIAL_ENV` coincidir com `APP_ENV`.
4. Valide a configuração sem publicar valores:
   `docker compose --env-file <arquivo-seguro> -p markina-gallery -f docker/docker-compose.yml config --quiet`.
5. Após aprovação do deploy, use dados sintéticos para comunicar um pagamento,
   decidir no painel e conferir os estados `queued`, `sent` ou `failed`.
6. Nunca copie credenciais entre homologação e produção nem mostre payloads do
   provedor em logs de validação.

## Templates controlados

Em **Configurações → Mensagens de pagamento**, o fotógrafo edita separadamente
confirmação e pagamento não localizado. São aceitos texto simples e somente:

- `{{cliente}}` — nome congelado ou nome atual autorizado;
- `{{pedido}}` — referência curta do UUID público do pedido;
- `{{galeria}}` — nome da galeria privada.

HTML, URLs, variáveis desconhecidas, chaves soltas e caracteres de controle são
recusados pelo servidor. O worker renderiza o template no envio; o corpo não é
armazenado na caixa de saída nem escrito em logs.

## Falhas e reenvio

- Falha transitória volta à fila até `WHATSAPP_MAX_ATTEMPTS`.
- Falha permanente, destino divergente ou configuração inválida fica `failed`
  com erro sanitizado, sem telefone ou corpo da mensagem.
- O painel permite reenfileirar falha que ainda esteja abaixo do limite. Ao
  atingir o limite, corrija a causa e registre uma decisão operacional antes de
  qualquer intervenção no banco; não altere contadores manualmente.
- A decisão financeira e o histórico continuam válidos mesmo se o WhatsApp
  estiver indisponível.

## Rollback

1. Para interromper efeitos externos, altere o arquivo seguro do ambiente para
   `WHATSAPP_PROVIDER=sandbox` e publique somente pelo fluxo aprovado. Não
   remova registros da caixa de saída.
2. Preserve comunicações, decisões, tentativas e auditoria. Um rollback de
   código pode ocultar a interface, mas não deve reverter pagamentos
   confirmados nem apagar histórico.
3. A migration `20260829_0014` é aditiva. Downgrade remove tabelas de
   comunicação, templates e outbox; portanto só pode ocorrer com autorização
   humana explícita e após inventário/backup exclusivo da Markina.
4. Nunca restaure o banco automaticamente, nunca use prune e nunca execute
   `docker compose down` fora do escopo explícito
  `-p markina-gallery -f docker/docker-compose.yml`.
