## Purpose

Definir modelos comerciais globais reutilizáveis e cálculo progressivo por parcelas, mantendo moeda brasileira, snapshots por galeria e totais autoritativos no backend.

## ADDED Requirements

### Requirement: Modos comerciais explícitos por Galeria pública
O sistema SHALL permitir configurar cada Galeria pública com `preço fixo` ou `preço progressivo por faixas`. O preço fixo SHALL aplicar o mesmo valor unitário a qualquer quantidade; o progressivo SHALL exigir a escolha de uma tabela global válida e materializar suas faixas na configuração da galeria.

#### Scenario: Preço fixo
- **WHEN** o fotógrafo escolhe preço fixo de R$ 7,00
- **THEN** o backend persiste 700 centavos e calcula qualquer seleção elegível como quantidade multiplicada por 700

#### Scenario: Tabela progressiva escolhida
- **WHEN** o fotógrafo seleciona uma tabela global no dropdown e salva a etapa Vendas
- **THEN** o sistema copia código, nome e faixas vigentes para a Galeria pública sem manter dependência mutável para o cálculo futuro

### Requirement: Cadastro global identificado de tabelas progressivas
O sistema SHALL permitir ao fotógrafo criar, editar, listar e desativar tabelas globais com código visível único, nome e faixas contíguas iniciadas em um. Somente a última faixa SHALL poder ficar sem limite superior, e valores unitários subsequentes SHALL NOT superar o valor da faixa anterior.

#### Scenario: Dropdown de tabelas
- **WHEN** a etapa Vendas consulta os modelos ativos
- **THEN** ela apresenta opções identificadas como `código — nome`, por exemplo `01 — Tabela escolar`, sem misturar modelos desativados

#### Scenario: Faixas inválidas
- **WHEN** o fotógrafo envia intervalo ausente, sobreposto, descontínuo ou com valor crescente
- **THEN** o backend rejeita a tabela e informa a faixa problemática sem persistência parcial

#### Scenario: Modelo global alterado
- **WHEN** uma tabela já usada é editada ou desativada
- **THEN** galerias e pedidos existentes preservam seus snapshots e somente uma nova escolha utiliza a versão atualizada

### Requirement: Cálculo progressivo por parcelas
O backend SHALL calcular cada unidade pelo valor da parcela em que sua posição se encontra e SHALL devolver detalhamento por faixa, quantidade, subtotal, total e economia. O frontend SHALL NOT recalcular autoridade comercial por conta própria.

#### Scenario: Sessenta fotos em duas faixas
- **WHEN** a tabela define fotos 1–30 a 700 centavos e 31–60 a 600 centavos e a cliente seleciona 60 fotos
- **THEN** o total é 39.000 centavos, composto por 21.000 e 18.000 centavos

#### Scenario: Economia progressiva
- **WHEN** a seleção alcança uma faixa com valor inferior à primeira
- **THEN** o orçamento informa a economia em relação a precificar toda a quantidade pelo valor-base da primeira faixa

#### Scenario: Pedido criado
- **WHEN** a cliente confirma a conferência comercial
- **THEN** o pedido congela modo, código e nome da tabela, faixas, parcelas, economia e total sem depender da configuração posterior

### Requirement: Entrada e exibição em moeda brasileira
O painel SHALL aceitar e exibir valores no formato de moeda brasileira, normalizando-os para centavos inteiros antes da persistência. Entradas ambíguas, negativas ou com precisão superior a centavos SHALL ser rejeitadas.

#### Scenario: Valor válido
- **WHEN** o fotógrafo informa `R$ 7,00`
- **THEN** a interface envia 700 centavos e volta a apresentar `R$ 7,00` após recarregar

#### Scenario: Valor malformado
- **WHEN** o campo recebe texto que não representa valor monetário brasileiro válido
- **THEN** a etapa permanece aberta, identifica o campo e não altera a configuração persistida

### Requirement: Migração comercial sem reinterpretação silenciosa
O sistema SHALL preservar a semântica e os pedidos existentes durante a transição do preço por volume para o preço progressivo. Uma configuração legada com uma única faixa SHALL poder migrar para preço fixo equivalente; uma configuração legada com várias faixas SHALL permanecer identificada como `volume legado` e bloqueada para novos pedidos até revisão e conversão explícita pelo fotógrafo.

#### Scenario: Faixa legada única
- **WHEN** a migration encontra galeria com uma única faixa legada iniciada em um
- **THEN** ela materializa preço fixo equivalente sem alterar pedido, seleção ou total existente

#### Scenario: Várias faixas legadas
- **WHEN** a migration encontra duas ou mais faixas cuja semântica anterior precificava todas as unidades pela faixa alcançada
- **THEN** ela preserva a configuração como volume legado, não recalcula histórico e exige conversão explícita antes de novo checkout

#### Scenario: Conversão revisada
- **WHEN** o fotógrafo abre uma galeria marcada como volume legado, escolhe preço fixo ou tabela progressiva e confirma a conversão
- **THEN** somente novas cotações usam o novo snapshot e todos os pedidos anteriores permanecem inalterados
