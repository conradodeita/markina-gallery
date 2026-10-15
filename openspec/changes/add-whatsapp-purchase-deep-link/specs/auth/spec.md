# Spec Delta

## ADDED Requirements

### Requirement: Retorno interno validado após OTP

O sistema SHALL preservar durante o desafio OTP um destino interno permitido no mesmo host de origem, e SHALL revalidar a propriedade do pedido e o vínculo da cliente antes do redirecionamento final.

#### Scenario: Retorno ao pedido autorizado

- **WHEN** a cliente conclui OTP iniciado por link de um pedido próprio no subdomínio ativo
- **THEN** o backend redireciona para Compras nesse mesmo tenant e o pedido solicitado

#### Scenario: URL externa ou destino sem autorização

- **WHEN** o destino recebido é externo, malformado ou identifica pedido de outro cliente/tenant
- **THEN** o sistema não redireciona para ele nem revela sua existência e encaminha a cliente à biblioteca segura do tenant autenticado

### Requirement: Reautenticação de Compras no subdomínio canônico

O sistema SHALL permitir que uma cliente já cadastrada solicite OTP para retornar a Compras a partir do hostname canônico do fotógrafo. A consulta SHALL ficar limitada ao tenant desse hostname, a resposta SHALL ser neutra para cadastro presente ou ausente, e SHALL NOT permitir cadastro novo sem convite de galeria.

#### Scenario: Cliente existente retorna ao pedido
- **WHEN** uma cliente existente abre o link de Compras, informa seu telefone e valida OTP no subdomínio do fotógrafo do pedido
- **THEN** a sessão é criada somente para o cadastro daquele tenant e o retorno interno de Compras é revalidado para essa cliente

#### Scenario: Mesmo telefone em dois fotógrafos
- **WHEN** o mesmo telefone existe em A e B e o cliente solicita OTP em A
- **THEN** somente o cadastro de A é consultado e nenhum dado, sessão, challenge ou destino de B é usado

#### Scenario: Cadastro inexistente
- **WHEN** o telefone não possui cadastro no tenant do hostname
- **THEN** a resposta pública não revela a ausência e nenhum OTP válido, sessão ou cadastro novo é criado
