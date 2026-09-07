# Diretório e lifecycle de clientes

## Objetivo e identidade

`/admin/clients` é o diretório global do fotógrafo. Ele funciona sem galerias e
reutiliza a mesma entidade `Client` usada na etapa 05. O telefone normalizado em
E.164 é a identidade canônica: cadastrar ou trocar um número nunca deve criar uma
segunda pessoa silenciosamente.

A troca de telefone mantém o UUID, os vínculos e o histórico. O novo número exige
OTP; após a confirmação, todas as sessões de cliente do UUID são revogadas. O
número anterior fica aposentado em `client_phone`. Estados OTP são atribuídos
somente ao número canônico/ativo atual, pois um número aposentado pode pertencer a
outra pessoa no futuro.

## Contratos administrativos

- `GET /admin/clients?query=&cursor=&limit=`: busca por nome/telefone, ordenação
  estável por nome normalizado + UUID, cursor opaco e agregados de Galerias
  públicas, privadas e pedidos. A consulta tem quantidade constante de queries.
- `POST /admin/clients`: cria uma cliente sem exigir galeria.
- `PATCH /admin/clients/{client_id}`: altera apenas o nome da mesma identidade.
- `POST /admin/clients/{client_id}/phone`: consome o desafio OTP do novo telefone
  e altera o número da mesma identidade.
- `GET /admin/clients/{client_id}/deletion-inventory`: classifica as consequências
  sem retornar dados de outras pessoas.
- `DELETE /admin/clients/{client_id}`: exige `Idempotency-Key` de 12 a 128
  caracteres e devolve um recibo síncrono após o commit.

Todas as rotas são exclusivas de sessão administrativa. A página global e a etapa
05 usam os mesmos formulários de cadastro e edição para não manter regras
divergentes.

## Classificação de exclusão

`operational_removable` inclui cadastro, registros de telefone, acessos e registros
públicos, memberships, capabilities, seleções, favoritos, visualizações,
comentários, sessões, OTPs atribuíveis ao número atual, notificações de membership
e buscas faciais transitórias.

`commercial_protected` inclui pedidos e itens, comunicações/notificações de
pagamento, entregas comerciais ligadas à origem persistida e mídias do histórico.
Qualquer quantidade maior que zero nessa classe impede a exclusão definitiva.
Entregas comerciais são associadas pelos UUIDs de sua comunicação/outbox, nunca
somente pelo telefone mutável.

## Efeitos de uma exclusão permitida

A operação bloqueia a identidade, revalida o inventário antes do delete e executa
o grafo em uma transação. Uma privada exclusiva da cliente e sem histórico é
apagada com suas referências operacionais. Uma privada compartilhada permanece;
somente membership e interações da cliente são removidos, e outro membro válido
assume a referência de proprietário quando necessário.

Galerias públicas, pastas, JPEGs, configurações, outras clientes e interações de
terceiros permanecem. A referência enviada para uma busca facial é removida do
armazenamento físico após o commit; embeddings e candidatos transitórios já foram
removidos na transação.

O item desaparece imediatamente da interface. Repetir a mesma chave idempotente
retorna o mesmo recibo, sem novo delete nem nova auditoria. Reutilizar a chave para
outro UUID é recusado.

## Auditoria e minimização

`client_deletion_receipt` guarda somente o fingerprint SHA-256 da chave idempotente,
UUID alvo sem FK, ator, fingerprint do inventário, estado, contagens e timestamps UTC. O evento
`client.deleted_without_history` segue a mesma minimização. Nome, telefone, chave
PIX, OTP e conteúdo comercial não entram no recibo ou na auditoria.

## Migration e rollback

`20260907_0047` sucede `20260906_0046` e cria apenas a tabela de recibos e seus
índices. O upgrade não altera clientes, galerias ou pedidos existentes. O rollback
preferencial é reverter a aplicação mantendo o schema aditivo. O downgrade
estrutural remove somente os recibos; depois disso, retries antigos deixam de ter
resultado idempotente, portanto ele só deve ocorrer com a versão antiga já ativa e
sem exclusões em andamento.

Antes de homologação, validar `alembic current`, executar a suíte de migration e
confirmar que o head esperado é `20260907_0047`. Nenhuma limpeza de dados ou deploy
é implícita neste procedimento.
