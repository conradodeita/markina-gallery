# Ciclo de vida, acesso e privacidade de galerias

Este documento descreve o contrato operacional implementado pela change
`improve-gallery-and-client-data-lifecycle`. “Galeria pública” é o nome do
produto para a origem compartilhável; ela nunca é pública sem autenticação.
“Galeria privada” é a visão exclusiva de uma cliente identificada pelo telefone
comprovado por OTP.

## Exclusão e desvinculação assíncronas

As operações destrutivas administrativas usam pré-inventário e execução
assíncrona:

- `GET /admin/parent-galleries/{id}/deletion-inventory` antecipa o que será
  removido e preservado;
- `DELETE /admin/parent-galleries/{id}` exige `Idempotency-Key` e responde
  `202 Accepted`;
- `GET /admin/parent-galleries/{id}/clients/{client_id}/unlink-inventory`
  antecipa a desvinculação individual;
- `DELETE /admin/parent-galleries/{id}/clients/{client_id}` também exige chave
  idempotente e responde `202 Accepted`;
- `GET /admin/gallery-lifecycle-operations/{operation_id}` publica estado,
  progresso e ações permitidas pelo backend;
- `POST .../{operation_id}/cancel` só funciona antes da primeira remoção
  física;
- `POST .../{operation_id}/retry` retoma uma operação em `failed` sem repetir
  etapas já confirmadas.

O cliente HTTP deve seguir `status_url`, `progress` e `actions`. Não deve inferir
se pode cancelar, repetir ou continuar consultando. Os estados duráveis são
`queued`, `preparing_history`, `removing_storage`, `removing_records`,
`completed`, `failed` e `cancelled`. Repetir a mesma chave devolve a mesma
operação; outra chave concorrente para o mesmo alvo é recusada.

Excluir uma Galeria pública revoga sua descoberta, links e vínculos públicos,
mas conserva galerias privadas e a única cópia de cada foto ainda referenciada
por alguma delas. Desvincular uma cliente remove apenas a relação e a privada
daquele par. Em ambos os casos, cadastro e histórico comercial ficam fora do
grafo operacional removido.

## Modos de acesso e tokens

- `standard`: link público opaco + OTP pode criar o vínculo ativo e liberar a
  navegação;
- `invite_only`: exige vínculo prévio ou convite individual compatível com o
  telefone comprovado;
- `collective_protected`: não entrega grade pública; o vínculo permanece
  pendente para um fluxo facial futuro, que continua desabilitado.

Tokens de link e convite possuem alta entropia, são apresentados somente na
emissão/rotação e persistidos apenas como hash. UUID não é credencial. Revogação,
rotação, expiração, escopo e consumo são validados no backend. Uma sessão já
autenticada pode aplicar o link sem novo OTP, mas nunca recebe acesso a outra
cliente ou a outra origem por consequência.

## Disponibilidade, seleção e propriedade

`DerivedGalleryPhoto` representa uma foto disponível na privada;
`PhotoSelection` representa uma escolha comercial da cliente. A origem da
disponibilidade é `admin`, `client` ou, somente após change própria, `facial`.
Disponibilizar uma foto pela administração não a seleciona nem a compra.

A primeira seleção autorizada cria ou reutiliza atomicamente uma única privada
por `Galeria pública + Client`. Seleções posteriores da mesma origem usam essa
privada. Remover a última seleção de origem `client` encerra a privada somente
se não restar referência disponível nem bloqueio comercial. Referência `admin`
mantém a privada ativa com zero seleções. Uma seleção posterior na Galeria
pública cria uma nova privada operacional quando a anterior já foi encerrada.

## Herança e congelamento comercial

Preço e faixas, PIX, mensagens, favoritos, comentários e apresentação pertencem
à Galeria pública e são herdados por suas privadas. O prazo efetivo é
materializado ao criar a privada. Ao criar o pedido, termos, nomes, valores, PIX
e itens são congelados em snapshots; alterações futuras na origem não alteram o
pedido existente.

A política comum de remoção é:

- carrinho sem pedido pode ser descartado;
- pedido `pending` sem pagamento comunicado é cancelado com auditoria;
- comunicação `pending_review` bloqueia a remoção até decisão administrativa;
- compra `confirmed` exige snapshots e mídia histórica mínima pronta antes da
  remoção operacional.

## Armazenamento e histórico

O manifesto físico contém somente originais e derivados operacionais sem
referência privada. Caminhos são derivados de registros internos, confinados aos
diretórios da Markina e tratados de forma idempotente quando o arquivo já não
existe. Falha parcial mantém a operação retomável.

Itens comprados preservam metadados imutáveis, uma prévia histórica protegida e
a entrega final ou referência segura em armazenamento histórico separado. Isso
não autoriza reter todos os originais nem fotos não compradas. A política e a
minimização comercial detalhadas estão em `docs/RETENCAO-HISTORICO-COMERCIAL.md`;
nenhum prazo legal é inventado pelo sistema.

## Privacidade do OTP

Enquanto o OTP pode ser entregue e validado, o desafio e a entrega guardam o
telefone necessário, e o código existe somente como hash e cifra temporária.
Após consumo autorizado, negação terminal ou quinta tentativa inválida, nome,
telefone, destinatário e cifra são apagados. Auditoria e rate limit usam
fingerprint HMAC não reversível.

Desafios abandonados são minimizados depois de expirarem e ultrapassarem
`AUTH_OTP_PII_RETENTION_MINUTES` (padrão: 60 minutos). O worker verifica essa
limpeza a cada `AUTH_OTP_CLEANUP_INTERVAL_SECONDS` (padrão: 60 segundos). A
reexecução é idempotente e um OTP ainda válido não é limpo antecipadamente.

`AUTH_PII_FINGERPRINT_SALT` é segredo obrigatório fora de desenvolvimento, deve
ser longo, aleatório, fornecido pelo ambiente seguro ao API e ao worker e nunca
persistido no banco ou no Git. A rotação desse segredo altera fingerprints
futuros e deve ser planejada considerando a janela do rate limit e os desafios
ainda ativos.

## Recuperação e rollback

Antes de `removing_storage`, cancelamento devolve a Galeria pública ao estado
ativo. Depois desse marco não existe promessa de restauração; a recuperação é
retomar a mesma operação até concluir. Rollback de aplicação antes de qualquer
remoção física pode acompanhar downgrade estrutural. Após dados operacionais
terem sido removidos, deve-se manter a versão compatível e concluir/inspecionar
os manifestos; downgrade não recria mídia nem relações apagadas.

A migration `20260831_0031` é estruturalmente reversível e substitui campos já
minimizados por marcador não pessoal ao voltar ao schema anterior. Um deploy
deve fornecer o salt seguro antes de receber tráfego de autenticação.
