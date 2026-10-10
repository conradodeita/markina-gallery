## Why

O processamento de pastas privadas está fragmentado entre controles herdados e ações manuais. Isso torna pouco claro quando reconhecimento facial e ajuste das prévias serão executados e permite que ajustes de uma pasta dependam da galeria pública.

## What Changes

- Tornar o reconhecimento facial automático para fotos enviadas a pastas privadas quando o rollout operacional global estiver habilitado; remover escolhas de herança, permissão ou pausa por pasta.
- Manter o progresso do reconhecimento e renomear a retentativa para “Refazer reconhecimento”.
- Dar a cada pasta privada (`audience_scope = selected`) configuração própria de ajuste automático, ativa com intensidade 75% e exposição 0,0 EV por padrão, sem herdar valores da galeria pública.
- Encadear o ajuste das prévias após o reconhecimento facial da foto terminar. Alterar intensidade ou exposição cancela trabalhos obsoletos e agenda novamente usando a fonte limpa original da foto, sem acumular ajustes.
- Remover as escolhas de herança/personalização/desligamento e os botões manuais de processar e salvar; manter progresso e aplicar mudanças de configuração imediatamente.
- Empilhar os cartões existentes do Acervo do Cliente no desktop, com reconhecimento acima do ajuste, preservando o recolhimento atual da pasta.

## Capabilities

### New Capabilities

- `media-storage/private-folder-processing`: automatização e configurações de processamento isoladas por pasta privada.
- `privacy-biometric/automatic-facial-availability`: disparo automático por foto privada respeitando os gates operacionais globais existentes.

## Impact

Painel existente do Acervo do Cliente; API e configuração de pasta existentes; integração entre fila facial e fila de ajuste; invalidação idempotente de trabalhos; testes e documentação. Não é necessária nova tabela: `FolderProcessingSettings` já persiste as configurações por pasta. O rollout facial global, controles de acesso, retenção biométrica e proteção das prévias continuam obrigatórios.

## Non-goals

Alterar o rollout global facial, autorizar processamento facial em produção, habilitar processamento quando o gate operacional estiver desligado, reprocessar automaticamente o acervo inteiro, alterar originais ou enfraquecer proteção/controle de acesso.
