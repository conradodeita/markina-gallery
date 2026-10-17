# Spec Delta

## Purpose

Define quando clientes autorizadas recebem o aviso de novas fotos privadas para que o evento acompanhe a disponibilidade real das prévias, independentemente da ordem entre publicação da pasta e conclusão do processamento.

## ADDED Requirements

### Requirement: Avisar novas fotos ao concluir upload privado
O sistema SHALL criar o evento configurável `private_photos_ready` quando o lote de upload de uma pasta privada da cliente terminar e ao menos uma nova prévia protegida estiver pronta e disponível. O aviso SHALL respeitar os canais habilitados, revalidar vínculo e acesso no envio e deduplicar por lote e cliente. Uploads na Galeria pública SHALL NOT gerar este evento.

#### Scenario: Lote privado concluído
- **WHEN** o fotógrafo termina o upload de novas fotos numa pasta privada e o processamento disponibiliza ao menos uma prévia
- **THEN** o sistema cria o aviso para cada membro ativo autorizado, sem exigir uma etapa manual de publicação

#### Scenario: Upload na Galeria pública
- **WHEN** fotos são enviadas à pasta de conteúdo da Galeria pública e ficam automaticamente disponíveis
- **THEN** o sistema não cria o evento `private_photos_ready`

#### Scenario: Lote privado ainda aberto
- **WHEN** o lote da pasta privada ainda está recebendo arquivos
- **THEN** o sistema não cria aviso prematuro

#### Scenario: Canais configurados independentemente
- **WHEN** o evento é criado e somente um entre WhatsApp e push está habilitado
- **THEN** somente o canal habilitado recebe a entrega, sem fallback que ignore a configuração

#### Scenario: Reprocessamento ou retomada
- **WHEN** o mesmo lote é retomado ou processado novamente após gerar o aviso
- **THEN** o sistema não cria entrega duplicada para a mesma cliente

#### Scenario: Identidade composta excede o limite persistido
- **WHEN** os UUIDs completos da pasta, lote, vínculo e cliente e o conjunto de fotos produzem uma chave maior que os 192 caracteres aceitos no banco
- **THEN** o sistema SHALL persistir uma representação determinística que caiba no limite, preservando a identidade completa para deduplicação e sem interromper a conclusão do lote
- **AND** chaves anteriores que já cabem no limite SHALL continuar identificando o mesmo aviso

#### Scenario: Novo lote com as mesmas fotos
- **WHEN** outro lote autorizado da mesma pasta contém as mesmas fotos para a mesma cliente
- **THEN** o novo lote SHALL gerar seu próprio aviso e sua retomada SHALL manter somente uma entrega por canal/dispositivo elegível

#### Scenario: Nenhuma prévia privada disponível
- **WHEN** o lote privado termina sem qualquer nova prévia pronta e disponível
- **THEN** o sistema não anuncia fotos indisponíveis
