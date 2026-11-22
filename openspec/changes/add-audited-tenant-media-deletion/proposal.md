# Proposal

## Why

O sistema sinaliza uma revisão manual dez anos após o encerramento, mas ainda não oferece uma forma segura de o proprietário remover mídia fria. O método de storage já admite exclusão idempotente, porém o worker não executa `delete_remote`; sem um recibo completo, não é seguro remover o verificador protegido de CPF usado para recuperar a conta.

## What Changes

- Disponibilizar no console privado uma ação manual, reautenticada e auditada do `PlatformOwner` para remover definitivamente a mídia arquivada de uma conta encerrada após o marco de revisão de dez anos.
- Reutilizar a fila global e o adapter de arquivo frio; excluir todos os objetos e manifestos dos ciclos arquivados do tenant, verificando a ausência remota e registrando progresso retomável por objeto e por ciclo.
- Manter recuperação e reabertura bloqueadas após exclusão; falhas parciais ou resultados incertos permanecem pendentes e preservam o verificador protegido de CPF até a comprovação integral.
- Remover o verificador somente após recibo agregado completo. Preservar registros operacionais, financeiros e o protocolo de aceite; não criar expurgo automático nem apagar conteúdo real durante testes locais.

## Capabilities

### New Capabilities
- `media-storage/gallery-media-archive`: exclusão remota explícita e verificável de mídia arquivada no ciclo de arquivo frio já definido.

### Modified Capabilities
- `platform-admin/owner-console`: estado, confirmação e acompanhamento da exclusão manual pelo proprietário.

## Impact

Backend FastAPI/SQLAlchemy/Alembic, worker global de arquivo frio, adapter `MediaArchiveStorage`, console Next.js do proprietário e testes sintéticos. A implementação local não configura nem chama o Google Drive real, não executa migrations em bancos persistentes e não altera produção.
