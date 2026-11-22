## MODIFIED Requirements

### Requirement: Remoção integral do acervo de teste
O reset SHALL zerar dados operacionais e mídia exclusiva de teste somente quando não existir tentativa Orders enviada ou inbox financeira de qualquer tenant. Evidência financeira SHALL bloquear inventário e execução antes da exclusão. Ativos de marca e configuração Mercado Pago do proprietário SHALL permanecer preservados; preparações locais não enviadas podem ser removidas como dados operacionais.

#### Scenario: Resultado vazio
- **WHEN** a execução autorizada termina com writers pausados e sem evidência Orders enviada
- **THEN** as contagens operacionais e de arquivos de acervo são zero e os ativos/configurações do proprietário continuam disponíveis

#### Scenario: Link para mídia externa
- **WHEN** uma raiz é symlink ou um caminho aponta para fora do volume autorizado
- **THEN** a operação recusa a raiz ou remove somente o link interno, sem seguir ou excluir arquivos externos

#### Scenario: Evidência financeira em outra conta
- **WHEN** um fotógrafo diferente do proprietário possui tentativa Orders enviada ou inbox financeira
- **THEN** o inventário e a execução são recusados sem excluir contas, configurações, pagamentos ou mídia
