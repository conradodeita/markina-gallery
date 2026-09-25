## Purpose

Permitir ao fotógrafo disponibilizar manualmente o álbum final do Google Photos por pedido, com acesso claro pela cliente em Compras e sem histórico de mensagens no card administrativo.

## ADDED Requirements

### Requirement: Link de entrega administrado por pedido

O sistema SHALL permitir ao fotógrafo autenticado cadastrar, substituir e remover o link do álbum do Google Photos em cada pedido. O formulário SHALL ocupar o lugar do texto de mensagem e dos estados, contadores de tentativas e ações de reenvio no card de Vendas e pagamentos, preservando identificação, itens, valores e ações financeiras. A operação SHALL exigir o botão explícito "Enviar" para persistir/disponibilizar e agendar o aviso configurado, ou confirmação de remoção para retirar o link. Digitar SHALL NOT produzir esses efeitos. O sistema SHALL mostrar sucesso apenas após persistência e registrar autor, pedido, tipo de ação e data UTC sem copiar o URL para o log de auditoria.

#### Scenario: Salvar e retomar o link
- **WHEN** o fotógrafo preenche um link válido, clica em Enviar e recarrega a página
- **THEN** o campo mostra o link persistido somente naquele pedido e o histórico visual de mensagens não aparece

#### Scenario: Erro ao salvar
- **WHEN** a gravação falha
- **THEN** o formulário informa o erro e preserva o texto digitado sem apresentar a entrega como salva

#### Scenario: Atualizar ou remover
- **WHEN** o fotógrafo confirma a substituição ou a remoção do link
- **THEN** o próximo carregamento autorizado de Compras apresenta o novo destino ou o estado indisponível, respectivamente

### Requirement: URLs de álbum válidas e seguras

O sistema SHALL aceitar somente HTTPS, sem credenciais, portas não padrão ou caracteres de controle, nos formatos de compartilhamento `photos.app.goo.gl/<identificador>` e `photos.google.com/share/<identificador>`, preservando parâmetros necessários ao acesso. O sistema SHALL rejeitar outros destinos e valores acima de 2048 caracteres, sem buscar o endereço no servidor. Espaços externos SHALL ser removidos; valor vazio SHALL representar remoção do link.

#### Scenario: Link curto e link completo
- **WHEN** o fotógrafo informa um link nos formatos aceitos, incluindo parâmetros do compartilhamento
- **THEN** o sistema persiste o destino sem alterar seu identificador ou os parâmetros necessários ao acesso

#### Scenario: Destino inválido
- **WHEN** o fotógrafo informa HTTP, JavaScript, domínio semelhante ou subdomínio não autorizado, credenciais no URL ou caminho sem identificador de álbum
- **THEN** o sistema rejeita o valor com mensagem compreensível e conserva o link anterior

### Requirement: Botão de entrega em Compras

O sistema SHALL exibir em cada pedido de Compras um botão verde "Fotos disponíveis" quando houver link salvo e pagamento confirmado, e um botão cinza desabilitado "Fotos indisponíveis" nos demais casos. O botão ativo SHALL abrir o álbum em nova aba sem conceder acesso à janela de origem e sem transmitir referência da página. O estado SHALL ser identificável pelo texto e pela semântica acessível, além da cor. Prévias compradas, ampliação e dados do pedido SHALL permanecer disponíveis segundo as regras existentes.

#### Scenario: Álbum disponível
- **WHEN** a cliente abre seu pedido com pagamento confirmado e link de entrega salvo
- **THEN** ela vê as prévias existentes e pode abrir o álbum pelo botão verde mesmo sem expandir as prévias

#### Scenario: Álbum ainda não cadastrado
- **WHEN** a cliente abre um pedido sem link
- **THEN** ela vê o botão cinza "Fotos indisponíveis", sem destino clicável, mantendo acesso às prévias existentes

### Requirement: Isolamento e continuidade da entrega

O sistema SHALL fornecer o link somente ao fotógrafo autenticado ou à cliente proprietária de pedido com pagamento confirmado. Enviar, substituir e Reenviar aviso SHALL exigir pagamento confirmado no backend, sem alterar implicitamente esse estado. Remover link SHALL continuar permitido ao fotógrafo mesmo em pedido não confirmado. Cada pedido SHALL manter seu link independente, mesmo em PIX agrupado. Expiração da seleção e remoção do acervo SHALL preservar o link por pedido e as regras existentes do histórico comercial.

#### Scenario: Pedido ainda não confirmado
- **WHEN** o fotógrafo tenta Enviar ou Reenviar aviso para pedido pendente ou com pagamento não localizado
- **THEN** a interface explica que é necessário confirmar o pagamento e o backend rejeita a operação sem gravar novo link nem emitir aviso

#### Scenario: Pedido de outra cliente
- **WHEN** uma cliente tenta consultar ou alterar a entrega de pedido alheio, ou um visitante não autenticado tenta acessá-la
- **THEN** o sistema nega o acesso sem revelar o URL, e a cliente também não pode alterar a entrega do próprio pedido

#### Scenario: Pedidos no mesmo PIX
- **WHEN** o fotógrafo cadastra um álbum em um de dois pedidos do mesmo pagamento agrupado
- **THEN** somente o pedido editado apresenta "Fotos disponíveis" e o outro preserva seu link ou ausência de link

#### Scenario: Histórico após expiração ou exclusão de acervo
- **WHEN** a seleção expira ou as imagens da galeria são removidas
- **THEN** a cliente continua acessando o álbum de seu pedido e o estado das prévias segue a política existente de remoção de acervo

#### Scenario: Entrega não altera pagamento
- **WHEN** o fotógrafo envia ou remove um link
- **THEN** a operação preserva a decisão financeira, os valores e os itens congelados

#### Scenario: Correção de pagamento após entrega
- **WHEN** o fotógrafo devolve à revisão um pagamento confirmado que possui link
- **THEN** o link permanece cadastrado para o fotógrafo, mas a API da cliente deixa de fornecê-lo e Compras apresenta Fotos indisponíveis na próxima consulta; avisos pendentes da entrega anterior são invalidados

#### Scenario: Nova confirmação após correção
- **WHEN** o pagamento é novamente confirmado e o link continua cadastrado
- **THEN** o botão verde volta a aparecer sem aviso automático de entrega; o fotógrafo pode usar Reenviar aviso se desejar, sem reativar avisos antigos cancelados

### Requirement: Substituição do histórico visual de mensagens

O sistema SHALL remover o histórico visual de mensagens do card do pedido sem criar backup ou arquivo paralelo desse histórico. As filas técnicas compartilhadas e a auditoria operacional SHALL continuar funcionando conforme seus contratos. Enviar o link SHALL gerar o evento configurável de entrega descrito em `messaging/order-delivery-notification`; remover o link SHALL ser silencioso. Nenhuma dessas ações SHALL modificar a configuração dos avisos de pagamento.

#### Scenario: Disponibilização com aviso
- **WHEN** o fotógrafo clica em Enviar para disponibilizar um álbum
- **THEN** o botão torna-se disponível na próxima consulta de Compras e o aviso segue a configuração do evento de entrega, sem reintroduzir histórico de mensagens no card

#### Scenario: Fluxo financeiro preservado
- **WHEN** uma cliente comunica pagamento e o fotógrafo registra sua decisão
- **THEN** os avisos configurados seguem funcionando, sem reaparecer como histórico visual no card do pedido
