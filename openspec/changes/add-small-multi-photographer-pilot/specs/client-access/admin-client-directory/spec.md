# Spec Delta

## MODIFIED Requirements

### Requirement: Diretório global independente de galerias

Neste requisito, diretório global SHALL significar todas as clientes da conta do fotógrafo autenticado. Busca, leitura, edição, exclusão, recibos e auditoria SHALL ser limitados a essa conta. A unicidade e as reservas de telefone SHALL ser por conta; mesmo telefone em outra conta MUST NOT causar conflito, revelar cadastro ou ser alterado pela operação.

O sistema SHALL fornecer ao fotógrafo autenticado um diretório de clientes acessível pela navegação administrativa mesmo quando não existir nenhuma Galeria pública. A listagem SHALL permitir busca por nome ou telefone, cadastro e abertura da edição, e SHALL manter visíveis clientes vinculadas, indicando seus vínculos em vez de removê-las dos resultados.

#### Scenario: Administração sem galeria

- **WHEN** o fotógrafo abre Clientes sem possuir galerias
- **THEN** o sistema apresenta o estado vazio do diretório e permite cadastrar, buscar e editar clientes sem exigir a criação prévia de galeria

#### Scenario: Cliente já vinculada

- **WHEN** uma cliente retornada pela busca já possui um ou mais vínculos
- **THEN** o cadastro permanece visível com seus estados e quantidades agregadas, sem duplicar a identidade

### Requirement: Edição preserva a identidade canônica

Neste requisito, diretório global SHALL significar todas as clientes da conta do fotógrafo autenticado. Busca, leitura, edição, exclusão, recibos e auditoria SHALL ser limitados a essa conta. A unicidade e as reservas de telefone SHALL ser por conta; mesmo telefone em outra conta MUST NOT causar conflito, revelar cadastro ou ser alterado pela operação.

O sistema SHALL permitir alterar o nome da cliente e trocar seu telefone na mesma identidade. O telefone SHALL ser normalizado, verificado pelo fluxo vigente e permanecer único; a alteração SHALL preservar vínculos e histórico e SHALL NOT criar uma segunda cliente.

A solicitação administrativa da prova OTP SHALL derivar a conta do vínculo autenticado e conferir o UUID da cliente antes de emitir desafio/entrega, inclusive sem galeria. Ela MUST NOT usar entrada genérica de cliente sem contexto nem aceitar parâmetro como escolha de conta.

#### Scenario: Troca de telefone

- **WHEN** o fotógrafo confirma o novo telefone com a verificação exigida
- **THEN** o sistema atualiza a identidade existente, invalida acessos dependentes do número anterior conforme a política e mantém galerias e histórico associados ao mesmo UUID

#### Scenario: Telefone já utilizado

- **WHEN** o novo telefone normalizado já pertence a outra cliente
- **THEN** o sistema recusa a alteração sem mesclar cadastros nem revelar dados adicionais da outra identidade

### Requirement: Exclusão distingue operação de histórico comercial

Neste requisito, diretório global SHALL significar todas as clientes da conta do fotógrafo autenticado. Busca, leitura, edição, exclusão, recibos e auditoria SHALL ser limitados a essa conta. A unicidade e as reservas de telefone SHALL ser por conta; mesmo telefone em outra conta MUST NOT causar conflito, revelar cadastro ou ser alterado pela operação.

O sistema SHALL classificar o inventário da cliente em dependências operacionais removíveis e histórico comercial protegido. Vínculos, estados individuais e referências residuais de galerias já removidas, sessões, convites, seleções sem pedido, favoritos, comentários, visualizações, buscas faciais transitórias e galerias privadas sem histórico SHALL NOT, isoladamente, impedir a exclusão; pedidos, pagamentos, entregas e seus snapshots SHALL impedir a exclusão definitiva. A exclusão SHALL remover referências operacionais remanescentes à identidade dentro da mesma transação, preservando tombstones e auditorias de galerias e sem alterar dados de terceiros.

#### Scenario: Cliente sintética com privada sem compra

- **WHEN** o fotógrafo confirma a exclusão de uma cliente que possui somente vínculos e uma galeria privada sem histórico comercial
- **THEN** o sistema remove atomicamente a identidade e seu grafo operacional, encerra ou preserva a privada conforme existam outros membros e confirma a exclusão imediatamente na interface

#### Scenario: Cliente com histórico comercial

- **WHEN** o inventário encontra pedido, pagamento ou entrega preservável
- **THEN** o sistema bloqueia a exclusão definitiva, apresenta as categorias que justificam o bloqueio e orienta editar o telefone ou administrar os vínculos sem apagar o histórico

#### Scenario: Cliente com estado residual de galeria removida

- **WHEN** o fotógrafo confirma a exclusão de uma cliente sem histórico comercial cuja identidade ainda é referenciada por estado individual ou outra dependência operacional de uma galeria removida
- **THEN** o sistema inclui essas referências no inventário, remove-as atomicamente para concluir a exclusão e preserva o tombstone, auditoria e dados de terceiros da galeria

### Requirement: Exclusão isolada, idempotente e auditável

Neste requisito, diretório global SHALL significar todas as clientes da conta do fotógrafo autenticado. Busca, leitura, edição, exclusão, recibos e auditoria SHALL ser limitados a essa conta. A unicidade e as reservas de telefone SHALL ser por conta; mesmo telefone em outra conta MUST NOT causar conflito, revelar cadastro ou ser alterado pela operação.

A exclusão SHALL exigir confirmação explícita e chave idempotente, repetir o mesmo resultado para a mesma operação e ocorrer sob controle de concorrência. Ela SHALL preservar Galerias públicas, JPEGs, configurações, outras clientes, membros restantes e histórico de terceiros; a auditoria SHALL registrar UUID, ator, resultado e contagens, sem nome, telefone ou conteúdo comercial.

#### Scenario: Privada compartilhada

- **WHEN** a cliente excluída é membro de uma privada que ainda possui outra cliente
- **THEN** o sistema remove somente a associação e as interações individuais da cliente alvo, mantendo a privada e os demais membros inalterados

#### Scenario: Repetição da confirmação

- **WHEN** a mesma chave idempotente é reenviada após uma exclusão concluída
- **THEN** o sistema retorna o resultado anterior sem executar novamente efeitos ou auditorias materiais

### Requirement: Auditoria de exclusão permanece limitada e completa

Neste requisito, diretório global SHALL significar todas as clientes da conta do fotógrafo autenticado. Busca, leitura, edição, exclusão, recibos e auditoria SHALL ser limitados a essa conta. A unicidade e as reservas de telefone SHALL ser por conta; mesmo telefone em outra conta MUST NOT causar conflito, revelar cadastro ou ser alterado pela operação.

O evento de auditoria de exclusão SHALL manter uma referência curta ao recibo durável e SHALL respeitar o limite de tamanho da coluna persistida. O recibo SHALL permanecer como fonte autoritativa para UUID da cliente, ator administrativo, resultado, fingerprint do inventário e contagens completas; a exclusão SHALL NOT truncar nem descartar esses dados para caber no evento.

#### Scenario: Exclusão com grafo operacional extenso

- **WHEN** uma exclusão elegível remove várias categorias operacionais na mesma transação
- **THEN** o evento de auditoria referencia o recibo sem exceder o limite de 320 caracteres, o recibo conserva os dados completos e a transação conclui também em PostgreSQL
