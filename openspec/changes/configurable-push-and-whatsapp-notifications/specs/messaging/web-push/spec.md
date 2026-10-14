## Purpose

Permitir notificações push privadas e consentidas no navegador/aplicativo instalado de clientes e fotógrafo, sem ampliar o acesso às galerias.

## ADDED Requirements

### Requirement: Adesão por dispositivo e identidade

Admin autenticado e cliente autenticado SHALL poder ativar ou desativar push no dispositivo por ação explícita. O sistema SHALL explicar quando navegador não suporta, permissão foi recusada ou instalação na tela inicial é necessária; não insistir automaticamente nem confundir permissão do dispositivo com o interruptor global do admin. Cada inscrição SHALL pertencer à identidade autenticada no backend, nunca a uma identidade enviada livremente pelo navegador.

#### Scenario: Adesão e múltiplos dispositivos
- **WHEN** um usuário autoriza push em um dispositivo compatível
- **THEN** associa aquela inscrição ao usuário e entrega eventos futuros elegíveis aos seus dispositivos ativos, sem duplicar uma inscrição existente

#### Scenario: Saída e troca de usuário
- **WHEN** o usuário sai explicitamente, revoga o dispositivo ou outra conta assume aquela instalação
- **THEN** desativa a associação anterior e impede que a nova conta receba notificações destinadas à anterior; revogação de acesso impede novos avisos daquela galeria

### Requirement: Avisos curtos e navegação segura

O service worker SHALL apresentar o título/corpo transacional recebido sem precisar manter a página aberta, quando permitido pela plataforma. Não SHALL armazenar páginas privadas, fotos ou respostas de API em cache. O clique SHALL abrir apenas destino interno permitido, sujeito a login e autorização atuais. Nenhuma notificação SHALL transportar OTP, token de convite, fotografia, biometria, dados bancários ou URL que conceda acesso.

#### Scenario: Tela fechada
- **WHEN** uma inscrição ativa recebe um evento enquanto a página está fechada
- **THEN** o navegador pode exibir a notificação com o texto curto e arte configurada, respeitando suas permissões e preferências de apresentação

#### Scenario: Sessão expirada ou vínculo removido
- **WHEN** alguém toca um aviso sem uma sessão autorizada atual
- **THEN** deve autenticar-se ou recebe acesso negado, nunca adquirindo permissão pelo link da notificação

### Requirement: Transporte protegido e revogável

O sistema SHALL proteger inscrições e chaves de push contra exposição em logs/frontend indevido, validar destinos de provedor contra requisições a redes internas e permitir desativação operacional do transporte. Inscrições expiradas SHALL ser desativadas; falhas transitórias SHALL ter retentativas limitadas. Aceite pelo provedor não SHALL ser rotulado como leitura ou entrega garantida no celular.

#### Scenario: Endpoint inválido ou interno
- **WHEN** a inscrição aponta para endpoint não autorizado ou rede interna
- **THEN** rejeita sem realizar chamada ao endereço informado

#### Scenario: Inscrição expirada
- **WHEN** o provedor informa que a inscrição deixou de existir
- **THEN** desativa essa inscrição sem retentar indefinidamente e sem afetar outros dispositivos ou WhatsApp
