# Proposal

## Why

O inventário de preparação do checkout Orders confirmou Pillow 12.3.0 em seis workers especializados de produção, dentro das faixas de 41 alertas abertos, incluindo cinco críticos. API/worker geral já usam 13.0.0. Após explicação, o proprietário autorizou explicitamente corrigir primeiro esses seis processos, antes de retomar Mercado Pago. O PR Dependabot #258 já propõe o pin 13.0.0 no spike; reutilizar esse PR em vez de duplicá-lo.

## What Changes

- Fixar Pillow 13.0.0 nos manifests consumidores e atualizar o inventário de terceiros, sem outros upgrades.
- Construir candidatos ARM64 derivados dos seis IDs ativos, instalando somente o wheel oficial de Pillow, offline na etapa de build, com checksum validado.
- Provar igualdade das demais distribuições/Python/código/modelos e compatibilidade dos consumidores com entradas sintéticas, formatos, EXIF, resize e saídas de preview.
- Preparar publicação pontual com inventário/fingerprint, parada segura, suspensão/restauração de restart policy, saúde e rollback compatível sem migration.

## Capabilities

### New Capabilities

- `deployment-operations/specialized-pillow-security`: correção isolada por imagem com ensaio e recuperação verificáveis.

### Modified Capabilities

Nenhuma funcionalidade comercial ou regra de acesso/pagamento é alterada.

## Impact

`backend/requirements.txt`, `scripts/face_spike/requirements.txt`, inventário, testes/harness operacional e seis imagens. Não reconstruir pelos Dockerfiles normais que baixam modelos ou resolvem outros pacotes. Não trocar modelos/pesos, OpenCV, NumPy, PyTorch, LightCraft ou RawTherapee; não usar fotos reais, reindexar acervo, alterar credenciais ou misturar a publicação Orders. Avaliação proporcional de manutenção: nenhuma limpeza geral ou remoção de consumidor é necessária.
