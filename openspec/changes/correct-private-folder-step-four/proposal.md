# Proposal

## Why

A identificação das pastas privadas foi adicionada como uma seção separada na etapa 04, embora a necessidade seja identificar a cliente no próprio título de cada pasta. Além disso, fotos enviadas pela etapa 04 não notificam as clientes porque esse caminho não fecha um lote de upload.

## What Changes

- Remover da etapa 04 a seção adicional de galerias privadas e identificar cada pasta restrita no seu título com os nomes das clientes atribuídas.
- Fazer uploads de pastas restritas pela etapa 04 participarem do lote de upload e fechá-lo ao terminar, preservando notificações após o processamento e em envios parciais.
- Manter o comportamento de upload e apresentação das pastas comuns.

## Capabilities

### New Capabilities

### Modified Capabilities
- `gallery-sales/operational-gallery-interface`: identificação de pasta restrita no card existente e disparo consistente do lote a partir da etapa Imagens.
- `client-access/folder-audiences`: aviso de novas fotos restritas também para lotes enviados pela etapa Imagens, sem alterar destinatárias ou idempotência.

## Impact

Afeta a interface administrativa da etapa 04, a resposta da API administrativa de pastas para incluir nomes das clientes atribuídas, os endpoints existentes de lote de upload, testes frontend/backend e os hashes de API/web usados pelo preflight protegido de produção. Não requer migração de banco nem altera autorização de acesso às fotos ou serviços worker.
