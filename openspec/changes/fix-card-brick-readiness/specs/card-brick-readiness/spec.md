## ADDED Requirements

### Requirement: Formulário oficial legível
O checkout SHALL preservar cores coerentes dos campos oficiais em uma superfície clara isolada, inclusive quando o restante do site usa tema escuro, sem depender de classes internas geradas pelo SDK.

#### Scenario: Tema escuro no Pick Your Pic
- **WHEN** o cliente preenche o formulário oficial em página escura
- **THEN** os textos, campos e placeholders mantêm contraste legível sem coletar dados sensíveis fora dos componentes oficiais

### Requirement: Prontidão confirmada e recuperação segura
O checkout SHALL considerar os campos prontos somente após onReady e SHALL oferecer recuperação explícita após espera limitada, inclusive quando o controlador já existe ou o script ainda não carregou. Recuperação SHALL NOT enviar pagamento automaticamente.

#### Scenario: Controlador resolvido sem campos prontos
- **WHEN** o SDK retorna controlador mas não chama onReady em vinte segundos
- **THEN** a espera exibe mensagem de recuperação e opção de recarregar a página sem enviar dados de pagamento

#### Scenario: SDK lento ou indisponível
- **WHEN** o script não conclui o carregamento
- **THEN** a mesma espera limitada permite recuperação e retorno ao carrinho ou PIX

#### Scenario: Callback de envio atualizado
- **WHEN** o componente recebe outra referência do callback de envio para a mesma tentativa
- **THEN** mantém o Brick montado e usa o callback atual no envio autorizado

#### Scenario: Prontidão tardia
- **WHEN** onReady ocorre depois do aviso de demora
- **THEN** o formulário elimina o aviso de carregamento e permanece utilizável
