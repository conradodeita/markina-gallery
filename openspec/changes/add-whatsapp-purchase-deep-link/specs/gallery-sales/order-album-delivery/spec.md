## ADDED Requirements

### Requirement: Links de compartilhamento de álbum em serviços externos

O sistema SHALL aceitar e persistir URLs HTTPS de compartilhamento de serviços externos públicos de armazenamento, limitados a 2048 caracteres, sem consultar o destino. Valor vazio SHALL remover o link.

#### Scenario: Links de provedores externos
- **WHEN** o fotógrafo informa um link HTTPS de compartilhamento de Google Photos, Drive ou outro serviço externo público
- **THEN** o sistema persiste o URL original e o botão “Fotos disponíveis” em Compras o abre em nova aba

#### Scenario: Destino inválido ou não público
- **WHEN** o fotógrafo informa HTTP, JavaScript, URL com credenciais, porta não padrão, IP/local host, host malformado, caracteres de controle ou mais de 2048 caracteres
- **THEN** o sistema rejeita o valor, conserva o link anterior e apresenta mensagem que solicita um link HTTPS público de compartilhamento

#### Scenario: Hostname e formato seguros
- **WHEN** o fotógrafo informa hostname sem DNS público válido, IP literal, hostname local/privado, espaços internos ou caracteres de controle/backslash
- **THEN** o sistema rejeita o link sem fazer requisição ao host informado

#### Scenario: Caminho e tokens de compartilhamento
- **WHEN** um link externo inclui parâmetros de acesso no caminho, query ou fragmento
- **THEN** o sistema preserva esses componentes exatamente e não faz requisição de rede para validá-los

### Requirement: Link externo continua restrito à compra do cliente

O sistema SHALL manter o URL externo salvo no pedido do cliente e SHALL exibi-lo somente no botão “Fotos disponíveis” daquela compra, depois das verificações de propriedade e situação financeira existentes. O aviso WhatsApp SHALL conter apenas o `{{link_compras}}` interno ao pedido, tenant e hostname canônico do fotógrafo; SHALL NOT incluir o URL externo do álbum.

#### Scenario: Cliente abre seu pedido e álbum
- **WHEN** a cliente abre o link recebido, autentica-se no subdomínio do fotógrafo dono do pedido e consulta sua compra elegível
- **THEN** Compras posiciona a tela no pedido dela e exibe o botão “Fotos disponíveis” com o URL externo salvo naquele pedido

#### Scenario: Uma cliente possui pedidos com fotógrafos diferentes
- **WHEN** a cliente recebe o aviso de uma compra do fotógrafo A e também possui uma compra com o fotógrafo B
- **THEN** o link leva somente à compra dela com A, e nenhum pedido ou álbum de B é selecionado ou exposto
