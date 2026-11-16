# Design

## Context

Ver `proposal.md` e o requisito `WhatsApp próprio por fotógrafo SaaS` em `specs/messaging/spec.md`. O backend já expõe `POST /admin/whatsapp/channel/provision`, protegido por sessão, mesma origem e vínculo com um cadastro SaaS ativo. A resposta inclui o canal mascarado e o estado do pareamento; a rota não devolve credenciais do provedor. O `GET /admin/whatsapp/channel` representa a ausência de vínculo próprio com `provider: "unavailable"` e estado não pronto.

## Goals / Non-Goals

**Goals:**

- Distinguir primeiro provisionamento de edição do número por meio do estado do canal retornado pelo servidor.
- Preservar o comportamento do canal existente e impedir que a interface habilite pareamento antes da confirmação do servidor.
- Manter telefone, estado não pronto e feedback compreensível quando uma tentativa falhar.

**Non-Goals:**

- Alterar o provider, o protocolo Evolution, o schema ou as credenciais de servidor.
- Chamar um serviço WhatsApp real durante testes locais.
- Alterar regras de login, upload ou prontidão de notificações.

## Decisions

- **O estado do servidor escolhe a operação.** Quando `provider` for `unavailable`, salvar o número usa `POST /api/admin/whatsapp/channel/provision`; quando existir provider próprio, usa `PATCH /api/admin/whatsapp/channel`. Assim, a tela não precisa inferir ausência de credencial a partir de mensagem de erro nem armazenar estado paralelo sobre provisionamento.
- **A resposta de provisionamento é a única confirmação para seguir.** A interface valida a resposta com o mesmo guard `isChannel`, atualiza o canal e limpa o campo de entrada apenas após sucesso. O botão de pareamento depende de provider `evolution`, número esperado e ausência de operação em andamento.
- **Falha mantém possibilidade de nova tentativa sem prontidão falsa.** Uma resposta inválida ou erro HTTP não atualiza o canal para pronto, não inicia pareamento e conserva o número digitado. A mensagem ao usuário não inclui detalhes de infraestrutura ou credenciais.
- **O endpoint continua responsável pela autorização e idempotência.** A interface não envia tenant ID, nome de instância, segredo ou webhook; todos são determinados e validados no servidor. O caminho de edição não provisiona uma segunda instância.
- **Testes isolam a fronteira HTTP.** Testes do componente verificam POST no primeiro uso, PATCH em canal existente e falha fechada. Um teste de rota sintético verifica que o provisionamento exige o signup SaaS ativo e chama um provider substituto; nenhum teste fará requisição externa.

Alternativas consideradas: sempre usar `POST` foi descartada porque a rota é deliberadamente restrita ao primeiro provisionamento SaaS, enquanto canais provisionados/legados usam `PATCH`. Inferir o caso pelo texto de `last_error` foi descartado por ser instável e acoplar interface a detalhes operacionais.

## Risks / Trade-offs

- [O provider `unavailable` pode representar indisponibilidade além da ausência de credencial] → O `POST` responde com falha neutra e a tela mantém o canal não pronto; não há fallback para `PATCH`, que falharia fechado e poderia esconder problema de configuração.
- [Uma instância pode ser criada externamente e a resposta ao cliente se perder] → O endpoint existente usa identidade determinística/idempotente por tenant; nova tentativa recupera a mesma instância.
- [Cadastros legados não atendem ao gate de signup ativo] → Continuam no fluxo de edição já provisionado; não recebem provisionamento novo por esta tela.

## Migration Plan

Não há migração de dados. Alterar a tela e os testes locais, validar o endpoint com doubles sintéticos e atualizar esta change. O rollback local consiste em reverter somente os arquivos pertencentes a esta change após revisão do diff; nenhuma alteração externa ou em produção é necessária.
