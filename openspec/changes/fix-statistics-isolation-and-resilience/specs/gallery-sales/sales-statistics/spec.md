# Spec Delta

## Purpose

Definir estatísticas administrativas confiáveis para conversão e receita, com isolamento por cliente, histórico textual, paginação e exportações filtradas sem exposição indevida.

## ADDED Requirements

### Requirement: Estatísticas isoladas por cliente e galeria

O sistema SHALL calcular seleções, compras, receita, série temporal e listas no escopo efetivamente filtrado por cliente, Galeria pública, galeria privada, evento e período. Uma galeria privada compartilhada SHALL considerar somente as seleções e pedidos do cliente filtrado; sem filtro de cliente, a agregação SHALL aplicar a regra de fotos distintas sem misturar a autorização de uma consulta individual.

#### Scenario: Cliente membro de galeria compartilhada

- **WHEN** uma galeria privada possui seleções e pedidos de duas clientes e o fotógrafo filtra uma delas
- **THEN** contagens, receita, gráfico e listas retornam somente os dados da cliente filtrada

### Requirement: Histórico textual nas estatísticas

O sistema SHALL usar o identificador e o nome congelados do item comercial quando o ativo operacional tiver sido removido, sem emitir `None`, identificador vazio, URL de mídia ou PII.

#### Scenario: Foto removida após compra confirmada

- **WHEN** o fotógrafo consulta ou exporta estatísticas de uma compra confirmada cuja foto operacional foi removida
- **THEN** a compra permanece contabilizada e identificada pelo snapshot textual do pedido

### Requirement: Listas paginadas

O sistema SHALL retornar contagem total e uma página limitada de cada lista de fotos, com parâmetros de paginação validados. A interface SHALL permitir avançar e voltar entre páginas e SHALL reiniciar a página ao alterar filtros.

#### Scenario: Mais fotos do que a página atual

- **WHEN** o resultado contém mais itens que o limite da página
- **THEN** o fotógrafo vê a contagem total, os controles de navegação e somente os itens da página solicitada

### Requirement: Estado de erro da consulta

O sistema SHALL distinguir falha de autenticação, falha de consulta e resultado vazio. Falha de consulta SHALL NOT ser apresentada como contagem ou receita zero e SHALL oferecer nova tentativa sem apagar os filtros escolhidos.

#### Scenario: API de estatísticas indisponível

- **WHEN** a consulta de estatísticas retorna erro de rede ou resposta não bem-sucedida
- **THEN** a interface apresenta estado de erro acessível e ação de nova tentativa, sem mostrar indicadores vazios como se fossem dados reais

### Requirement: Exportação TXT coerente e filtrada

O sistema SHALL gerar os exports TXT de compradas e selecionadas sem compra a partir do mesmo escopo filtrado e da mesma regra de snapshots da consulta HTML. Cada linha SHALL conter somente identificador textual válido e nome de arquivo, em UTF-8, sem dados pessoais ou URLs.

#### Scenario: Exportação de cliente em galeria compartilhada

- **WHEN** o fotógrafo baixa qualquer TXT após filtrar uma cliente
- **THEN** o arquivo contém somente as fotos daquela cliente e não inclui nomes, pedidos ou fotos de outro membro

#### Scenario: Exportação após remoção do ativo

- **WHEN** uma foto comprada não possui mais ativo operacional
- **THEN** o TXT usa o identificador e o nome congelados do item comercial
