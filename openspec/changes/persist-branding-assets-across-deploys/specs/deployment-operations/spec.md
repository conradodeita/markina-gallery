## ADDED Requirements

### Requirement: Identidade visual durável entre publicações

O sistema SHALL conservar os arquivos de logo, favicon e ícone enviados pelo administrador em armazenamento persistente exclusivo do projeto. Reiniciar, reconstruir ou substituir o container da API SHALL NOT apagar esses arquivos nem exigir novo upload. As URLs, validações de upload, autorização administrativa e preferências existentes SHALL permanecer compatíveis.

#### Scenario: Recriação da API
- **WHEN** um ativo válido foi salvo e a API é recriada usando o mesmo armazenamento persistente
- **THEN** a URL existente entrega o mesmo arquivo, com hash idêntico e sem alteração do registro de branding

#### Scenario: Ícones derivados do aplicativo
- **WHEN** o aplicativo solicita os tamanhos suportados após a recriação
- **THEN** os ícones continuam disponíveis a partir da arte salva, preservando proporção e contrato de formato

### Requirement: Transição de branding sem perda silenciosa

O procedimento de deploy SHALL inventariar e preservar os arquivos legados ainda existentes antes de substituir a API na transição para armazenamento persistente. A transferência SHALL ser verificável, repetível e não destrutiva. Arquivos divergentes no destino SHALL bloquear a transferência afetada sem sobrescrita automática. O procedimento SHALL NOT apagar configurações nem declarar arquivos ausentes como recuperados.

#### Scenario: Arquivo legado presente
- **WHEN** a primeira publicação encontra um ativo legado válido e destino vazio
- **THEN** preserva uma cópia fora do container, transfere o arquivo e verifica seu hash antes de considerar a transição concluída

#### Scenario: Repetição ou conflito
- **WHEN** a transferência é repetida com um arquivo já existente
- **THEN** mantém o destino se os hashes forem iguais e interrompe com diagnóstico se forem diferentes, sem apagar nenhuma cópia

#### Scenario: Arquivo já ausente
- **WHEN** um ativo tem registro no banco, mas não há arquivo recuperável
- **THEN** registra a pendência de reenvio, preserva a configuração e mantém fallback seguro sem inventar arte ou impedir a recuperação dos demais ativos

### Requirement: Backup e isolamento de ativos de marca

O procedimento operacional SHALL incluir os bytes dos ativos de marca em backup restrito separado do dump SQL e orientar sua restauração por escopo exato, sem sobrescrita não autorizada. Armazenamento e cópias SHALL permanecer isolados do acervo fotográfico, dados biométricos e recursos de terceiros, sem novas portas públicas.

#### Scenario: Backup e restauração controlada
- **WHEN** o operador executa o procedimento documentado para os ativos de marca
- **THEN** a cópia possui verificação de integridade e permite recuperar somente esses ativos, sem restaurar banco ou alterar fotos, contas e preferências
