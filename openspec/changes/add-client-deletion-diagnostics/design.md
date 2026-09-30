# Design

## Context

Veja `proposal.md` — Why. A rota de exclusão já diferencia bloqueio comercial e conflito de inventário, e o recibo persistido permite repetir a mesma operação. A UI compartilhada converte respostas sem `detail` textual para uma mensagem genérica. Parte do trabalho auxiliar pode ocorrer depois do commit, portanto erro HTTP, rollback e remoção concluída não podem ser tratados como o mesmo estado.

## Goals / Non-Goals

**Goals:**

- Tornar uma falha HTTP correlacionável entre navegador e logs do backend por uma referência aleatória.
- Explicar se a resposta não confirmou a exclusão e mostrar o status HTTP quando o proxy retornar corpo sem JSON.
- Separar falha anterior ao commit de falha auxiliar posterior ao commit usando o recibo existente.
- Registrar somente campos de log permitidos por lista fechada.

**Non-Goals:**

- Adicionar endpoint de consulta de logs, painel de observabilidade geral, tabelas, retenção nova ou acesso a logs para clientes.
- Retornar mensagem bruta de banco, stack trace, SQL, constraint, UUID da cliente, telefone ou conteúdo operacional na resposta.
- Repetir automaticamente uma exclusão após timeout ou resposta não JSON.
- Alterar a classificação comercial, os dados removidos, a chave idempotente ou o fluxo de confirmação.

## Decisions

### 1. Identificador nasce e é validado no backend

Gerar UUID aleatório para cada requisição de exclusão no servidor e devolvê-lo em `X-Request-ID` e no objeto de erro esperado. Ignorar qualquer identificador externo fornecido pelo navegador para prevenir valores arbitrários em logs. A correlação não é autorização e não permite consultar dados.

Alternativa descartada: aceitar diretamente um cabeçalho arbitrário enviado pelo cliente. Sem validação forte ele permite conteúdo malicioso e colisões nos logs.

### 2. Exceções conhecidas mantêm seus contratos

Preservar respostas existentes para falta de autenticação, entrada inválida, cliente inexistente, bloqueio comercial e conflito de inventário. Em exceções não mapeadas, efetuar rollback antes do commit quando ainda aplicável e retornar mensagem estável, categoria estável e UUID. O frontend mantém a mensagem específica conhecida e apresenta o UUID somente quando presente.

Alternativa descartada: substituir toda falha por HTTP 500 genérico. Isso esconderia bloqueios já acionáveis e conflitaria com a resposta de histórico protegido.

### 3. Resultado posterior ao commit usa recibo idempotente

Manter o recibo como fonte de verdade. Se uma etapa auxiliar falhar depois do commit, consultar o estado já retornado/recibo pela mesma chave idempotente e reportar a exclusão concluída com uma referência de diagnóstico para a pendência auxiliar, sem afirmar rollback. Em uma resposta perdida ou não JSON, a interface informa falta de confirmação e orienta recarregar a listagem; não dispara outra mutação sozinha.

Alternativa descartada: marcar toda exceção como falha integral. Isso pode induzir a nova tentativa quando a transação já concluiu.

### 4. Logs têm esquema permitido e pequeno

Usar um evento estruturado com `request_id`, rota fixa, categoria allowlisted, status HTTP e estado transacional (`rolled_back`, `committed` ou `unknown`). Não anexar objeto da exceção, traceback, SQL, parâmetros, chave idempotente, corpo, UUID ou telefone. Cobrir erros inesperados sem criar novo armazenamento ou dependência.

Alternativa descartada: logar a exceção completa para depuração. O driver pode incluir SQL e valores de parâmetros.

### 5. Resposta não JSON mostra status sem especular sucesso

No cliente HTTP, preservar o status num erro tipado mesmo quando parsing JSON falha. A exclusão mostra texto neutro com HTTP status se disponível, recomenda recarregar a lista e verificar o recibo/listagem antes de nova ação. Nenhum corpo HTML do proxy é renderizado.

Alternativa descartada: exibir o corpo não JSON, que pode conter detalhes do proxy ou infraestrutura.

## Risks / Trade-offs

- [A aplicação gera o identificador mas uma resposta do proxy não o inclui] → essa UI apresenta somente o status HTTP e a falta de confirmação; nenhum código local será apresentado como se pudesse ser buscado nos logs.
- [Uma exceção após commit é reportada incorretamente como falha] → consultar o recibo da mesma chave e separar conclusão do banco de tarefas auxiliares.
- [Mensagens ou logs expõem PII por engano] → campos allowlisted, ausência de `exc_info`/payload e testes que procuram PII, SQL e segredo nas duas superfícies.
- [Código público é confundido com credencial] → gerar aleatoriamente, não permitir busca de dados pela referência e exigir sessão admin em toda rota existente.

## Migration Plan

1. Implementar o contrato e o log estruturado sem migration ou segredo novo.
2. Verificar com falhas sintéticas antes do commit, após o commit, resposta JSON conhecida e resposta não JSON do cliente; manter o inventário/comportamento comercial cobertos.
3. Validar lint, testes focados, OpenSpec estrito, typecheck/build e revisão de logs/respostas por ausência de PII e SQL.
4. Publicar somente após revisão humana e autorização operacional específica; inventariar topologia e saúde da homologação antes da execução.
5. Reverter aplicação ao SHA saudável anterior se a interface ou API falhar; não há migration a reverter. O recibo de lifecycle e o comportamento idempotente permanecem no banco.
