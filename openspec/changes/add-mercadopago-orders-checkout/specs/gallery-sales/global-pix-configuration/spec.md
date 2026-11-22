## ADDED Requirements

### Requirement: Habilitação independente do PIX manual
O sistema SHALL permitir ativar/desativar a emissão de novos pagamentos PIX manuais por tenant, independentemente do Mercado Pago, com senha/OTP, mantendo configuração e snapshots anteriores. O padrão do PIX SHALL continuar habilitado.

#### Scenario: PIX desabilitado
- **WHEN** fotógrafo desabilita PIX manual e confirma a alteração sensível
- **THEN** novas compras não oferecem esse método e histórico/instruções já comunicadas continuam disponíveis

#### Scenario: Nenhum método disponível
- **WHEN** ambos os mecanismos estão desabilitados ou indisponíveis
- **THEN** o checkout preserva a seleção e informa indisponibilidade sem criar cobrança

