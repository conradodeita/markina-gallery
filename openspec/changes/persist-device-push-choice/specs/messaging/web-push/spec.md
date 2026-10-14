## ADDED Requirements

### Requirement: Escolha persistente de push
O sistema SHALL memorizar a escolha de ativar ou desativar notificações por identidade autenticada e dispositivo/navegador. Ao retornar com a mesma identidade, SHALL reconciliar a inscrição do navegador e servidor, restaurando a adesão anterior quando a permissão nativa continuar concedida, sem novo prompt. O logout SHALL revogar a associação ativa e preservar somente a escolha. Uma conta diferente MUST NOT herdar essa adesão. O backend SHALL rejeitar registro cuja identidade esperada divergir da sessão atual.

#### Scenario: Retorno da mesma pessoa
- **WHEN** cliente ou admin retorna após reload ou novo login no mesmo navegador onde aderiu, com permissão concedida
- **THEN** a inscrição é mantida ou restaurada sem pedir que ative novamente

#### Scenario: Desativação voluntária
- **WHEN** a pessoa desativa os avisos
- **THEN** a escolha persiste e novos acessos não reativam automaticamente

#### Scenario: Conta diferente e resposta obsoleta
- **WHEN** a identidade muda durante a conciliação ou inscrição
- **THEN** o trabalho anterior não associa consentimento nem inscrição à nova conta

#### Scenario: Permissão ou armazenamento indisponível
- **WHEN** a permissão foi revogada, o navegador exige gesto ou a memória local foi removida
- **THEN** o sistema explica a situação e oferece ativação manual sem repetir solicitações nativas automaticamente

### Requirement: Convite de ativação sem insistência
O sistema SHALL oferecer a cliente e admin autenticados um convite acessível para ativar avisos no dispositivo elegível. O convite SHALL explicar a finalidade, permitir dispensa e solicitar permissão nativa somente após clique. Adesão ou dispensa SHALL impedir a repetição do convite naquele contexto; ativação manual permanece disponível.

#### Scenario: Primeiro acesso elegível
- **WHEN** a pessoa não possui escolha anterior e o dispositivo oferece push
- **THEN** recebe convite e pode ativar ou dispensá-lo sem bloquear o uso da galeria

#### Scenario: Convite já respondido
- **WHEN** a pessoa navega, recarrega ou retorna após aderir ou dispensar
- **THEN** o convite não reaparece e a escolha permanece disponível no controle de notificações
