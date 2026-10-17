# Proposal

## Why

Três referências reais autorizadas foram aceitas, mas retornaram zero candidatas em 2.691 fotos. O par positivo informado pelo proprietário (`DSC07382.jpg` → `LIV00862.jpg`) é rejeitado pelo limiar efetivo 0,750; o índice e seus fingerprints estão íntegros. A busca por toque recupera dez fotos. A interface também só conduz automaticamente buscas por toque, para o topo anterior à capa, sem garantir visibilidade das fotos encontradas.

## What Changes

- Preservar 0,750 como critério de correspondência firme e propor uma faixa independente de **possíveis correspondências** para referências SFace enviadas, com limite inicial revisável de 0,500, configurável e reversível. Para toque em região, adotar faixa independente de 0,600 após pedido explícito do proprietário em 17/10/2026. Não aplicar essas faixas à engine Gemma.
- Manter a classificação explícita `matched`/`ambiguous`, acesso autorizado, consentimento, retenção, modelo, índice, seleção e histórico.
- Conduzir uma única vez ao bloco efetivo de resultados quando uma consulta iniciada nesta página concluir com candidatas, tanto por upload/câmera quanto por toque. Fechar ampliação aberta e preservar rolagem de consultas restauradas e atualizações posteriores.
- Validar política e navegação pelo CI, e preparar entrega com inventário e aprovação protegida; testes reais continuam restritos aos arquivos e à galeria autorizados.
- Preparar o gate restrito aprovado separadamente em 17/10/2026: hashes exatos dos novos arquivos de apresentação/Compose e recusa de Docker fora desse escopo, sem instalar wrapper ou publicar antes da aprovação final.

## Capabilities

### New Capabilities

- `privacy-biometric/reference-match-classification`: classificação de candidatas de referência enviada com política distinta da correspondência firme e da busca por região.

### Modified Capabilities

- `gallery-sales/original-gallery-experience`: conclusão de busca iniciada na página conduz ao bloco de resultados, com foco acessível e sem saltos repetidos.
- `deployment-operations/facial-maintenance-scope`: manutenção admite exclusivamente o Compose revisado por blob e os arquivos relacionados, preservando autorização operacional separada.

## Impact

Configuração facial não secreta, worker de busca, contratos/testes existentes e página da Galeria pública/apresentação compartilhada. Sem nova dependência, modelo, índice, migration ou alteração de acesso. A publicação continua exigindo aprovação operacional específica; não editar `.env` ou secrets nesta preparação.

**Revisão recebida em 17/10/2026:** proprietário respondeu “Aprovar a proposta e implementar” à apresentação de 750 firme, faixa 500–750 somente para upload/câmera e direcionamento ao resultado. A faixa inicial 0,500 não representa calibração universal nem taxa de falsos positivos medida. A change anterior `improve-client-face-reference-capture` preservava o critério de aceitação; este aceite substitui somente essa restrição para possibilidades de upload. Em seguida, o proprietário solicitou: “quero que abaixe de 0,750 para 0,600 por toque no rosto ainda que possa trazer pessoas erradas”. Esse pedido aprova a faixa 600–750 como possibilidades por toque; o critério firme 750 continua preservado. Publicação e revisão da qualidade das candidatas continuam pendentes.
