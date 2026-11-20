# Spec Delta

## ADDED Requirements

### Requirement: Configuração e chave do backup operacional

O chamador de backup SHALL usar uma chave operacional própria e um vínculo protegido a uma única pasta global autorizada na conta Workspace escolhida. SHALL existir uma cópia offline da chave autenticada para recuperação sob custódia do proprietário.

#### Scenario: Configuração ou credencial incompatível

- **WHEN** a chave, instalação, origem, destino, escopo ou permissão divergir da configuração revisada
- **THEN** o chamador MUST abortar sem copiar o banco e registrar um código técnico sem expor credenciais

### Requirement: Autorização mínima da pasta global

O escopo OAuth SHALL permanecer `drive.file`. A seleção SHALL conceder acesso somente ao item escolhido. O token de acesso SHALL ser curto e ficar somente em memória no navegador; o refresh token MUST NOT ser exposto ao navegador.

#### Scenario: Seleção do destino global

- **WHEN** o proprietário selecionar pelo app a pasta `Pick-your-Pic Global` dentro de `Oracle-Production-Backups`
- **THEN** o app SHALL confirmar que o item é uma pasta privada de propriedade do usuário, sob a raiz esperada, autorizada para o app e capaz de receber arquivos; a seleção SHALL ser registrada sem token e a ferramenta root-only SHALL vincular seu ID à configuração protegida mantendo `enabled=false`

#### Scenario: Pasta não autorizada ou fora da raiz

- **WHEN** a pasta não for própria, estiver em drive compartilhado, não tiver autorização do app, estiver fora da raiz esperada ou não aceitar novos itens
- **THEN** o app MUST recusar o vínculo e o chamador MUST abortar sem copiar o banco

#### Scenario: Publicação sem ativação do backup

- **WHEN** o app e o runtime forem publicados antes da autorização do destino e da prova sintética
- **THEN** o serviço e o timer SHALL permanecer desativados e nenhuma cópia real SHALL ser iniciada

#### Scenario: Organização futura por tenant

- **WHEN** o operador preparar a raiz `Pick-your-Pic Tenants`
- **THEN** essa pasta SHALL permanecer apenas reservada até change própria implementar backup/restauração lógica por tenant, sem alterar a rotina de backup global

### Requirement: Execução interna agendada e manual

O chamador SHALL produzir o backup diário global e permitir acionamento manual pelo operador usando o mesmo lock e os mesmos controles, sempre dentro do escopo do projeto.

#### Scenario: Repetição da cópia diária

- **WHEN** a execução for repetida ou acionada manualmente para o mesmo ponto diário
- **THEN** o chamador SHALL reconciliar ou retomar o mesmo artefato e preservar cópias anteriores

### Requirement: Verificação pós envio e restauração distinta

O chamador SHALL enviar só o arquivo cifrado e verificar tamanho, SHA-256, autenticação do pacote e contexto antes de registrar cópia conferida. O registro de recuperação comprovada SHALL exigir restauração isolada independente.

#### Scenario: O destino confirma envio sem prova de recuperação

- **WHEN** o arquivo for aceito pelo Google sem um restore comprovado
- **THEN** a rotina MUST manter separados os estados de envio, leitura conferida e restauração comprovada

### Requirement: Ativação isolada e reversível

Instalar e ativar o agendamento SHALL exigir inventário, prova sintética e aprovação específica. MUST NOT recriar serviços de aplicação ou modificar backup e agendamento de terceiros.

#### Scenario: Necessidade de interromper rotina

- **WHEN** o operador desativar o agendamento
- **THEN** a rotina SHALL deixar de iniciar execuções novas e preservar os artefatos já gerados e o catálogo

### Requirement: Montagem protegida do seletor sem troca da web

A ponte SHALL oferecer operação fixa de configuração somente da API para o mount do Picker. SHALL preservar imagem e versão da API, web e testemunhas, usar lock e journal durável e publicar a base somente após prova de saúde, schema, configuração e flag facial. MUST NOT aceitar paths, mounts ou comandos arbitrários.

#### Scenario: Reconhecimento do suporte aprovado no gate de escopo

- **WHEN** o gate API/web avaliar o suporte desta operação
- **THEN** SHALL aceitar nominalmente `.github/workflows/production-google-picker-config.yml` e `scripts/test_production_app_picker.py`, mantendo a recusa de workflows, testes e workers não revisados e a verificação dos blobs de runtime

#### Scenario: Recriação autorizada para o Picker

- **WHEN** o operador aprovar o fingerprint atual e o arquivo protegido for válido
- **THEN** a ponte SHALL preservar a API anterior parada, criar somente a API com o bind read-only aprovado e manter a web intacta

#### Scenario: Interrupção da troca

- **WHEN** uma fase ficar incompleta ou qualquer identidade divergir
- **THEN** a ponte MUST bloquear repetição cega e oferecer inventário e recuperação explícitos somente da API, preservando todos os containers
