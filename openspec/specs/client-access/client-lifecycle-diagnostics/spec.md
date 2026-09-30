# client-lifecycle-diagnostics Specification

## Purpose

Definir como o fotógrafo recebe uma referência segura para diagnosticar falhas inesperadas em operações administrativas de lifecycle de cliente. A referência correlaciona resposta e log técnico sem expor dados pessoais nem alterar a decisão transacional.

## Requirements

### Requirement: Falha inesperada de exclusão inclui referência sanitizada

Quando uma tentativa autenticada de excluir uma cliente falhar por erro inesperado, o sistema SHALL retornar uma mensagem genérica e um identificador de diagnóstico aleatório, estável entre cabeçalho e corpo da mesma resposta. A interface SHALL exibir esse identificador de forma acessível junto ao status HTTP. O identificador SHALL NOT codificar UUID da cliente, telefone, conteúdo da requisição, horário, segredo ou valor comercial. Bloqueios comerciais e erros conhecidos SHALL conservar seus contratos acionáveis atuais.

#### Scenario: Falha inesperada anterior ao commit

- **WHEN** uma falha inesperada aborta a transação de exclusão
- **THEN** a API confirma rollback, registra a categoria técnica permitida sob o identificador e retorna uma mensagem genérica com o mesmo identificador, sem nome, telefone, UUID da cliente, SQL ou texto bruto da exceção

#### Scenario: Falha depois do commit

- **WHEN** uma operação auxiliar falha após o commit da exclusão
- **THEN** a resposta SHALL NOT afirmar que a transação foi desfeita; ela informa que o resultado foi concluído ou está sendo reconciliado, inclui identificador para diagnóstico e permite consultar novamente a listagem/recibo idempotente sem repetir efeitos

#### Scenario: Bloqueio comercial conhecido

- **WHEN** a exclusão é recusada por pedido, pagamento ou entrega protegida
- **THEN** a interface mantém a orientação atual e mostra as categorias de inventário protegidas, sem substituir esse resultado por erro inesperado genérico

#### Scenario: Resposta sem contrato JSON do proxy

- **WHEN** o navegador recebe resposta não JSON ou falha de transporte ao chamar a exclusão
- **THEN** a interface informa que não obteve confirmação, apresenta o status HTTP quando disponível e orienta recarregar e consultar a lista antes de tentar novamente, sem afirmar sucesso ou remoção

### Requirement: Correlação técnica não registra dados pessoais

O backend SHALL correlacionar a resposta de falha com um registro estruturado restrito a identificador aleatório, operação, status/categoria sanitizada e estado transacional conhecido. Logs e resposta SHALL NOT conter nome, telefone, UUID da cliente, corpo da requisição, chave idempotente, código OTP, credenciais, SQL, parâmetros ou texto bruto de exceção. Somente sessões administrativas autorizadas SHALL receber respostas detalhadas de inventário; a referência de diagnóstico, isoladamente, SHALL NOT conceder acesso a dados ou a outra rota.

#### Scenario: Busca por referência no log

- **WHEN** um operador autorizado correlaciona uma falha pela referência
- **THEN** encontra somente a categoria e o estado técnico registrados para aquela tentativa, sem conteúdo pessoal ou comercial

#### Scenario: Requisição inclui identificador externo inválido

- **WHEN** uma requisição fornece referência ausente, malformada ou excessiva
- **THEN** o backend substitui-a por identificador aleatório validado e não grava valor arbitrário enviado pelo cliente
