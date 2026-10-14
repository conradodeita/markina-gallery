# Proposal

## Why

O proprietário precisa entender o monitor sem interpretar tabelas técnicas, com dicas nos seis blocos operacionais escolhidos. A navegação recria a proteção de sessão, causando verificações visuais repetidas, e a mensagem de leitura presume compras/envios incertos. A recuperação automática recente será preservada.

## What Changes

- Manter Estado geral, Filas/uploads/processamento, Servidor/armazenamento, Fotógrafos/clientes, Incidentes/alertas e Capacidade/filas, com dicas acessíveis em linguagem simples.
- Retirar da tela principal Aplicação e experiência e Qualidade da coleta, mantendo suas informações na coleta e nos relatórios técnicos.
- Colorir a identificação dos fotógrafos e dos clientes de cada ramo conforme atividade confirmada: verde em active, vermelho em inactive, neutro nos demais estados, mantendo legenda textual.
- Nomear exportações como relatórios técnicos JSON/texto; manter avisos de dados ausentes, parciais ou antigos visíveis.
- Estabilizar a fronteira de sessão dentro do mesmo papel após validação inicial, revalidando rota/foco/período em segundo plano e removendo aviso de leitura após confirmação real.
- Preservar aviso de resultado incerto quando houve falha em mutação, sem repetir ações, e manter negação, expiração, validação inicial e isolamento de papéis.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations/system-monitor`: apresentação humana, dicas acessíveis e exportações técnicas preservadas.
- `auth/administrative-activity`: identificação colorida conforme evidência de atividade.
- `deployment-operations/admin-capacity-diagnostics`: dica de interpretação do snapshot.
- `auth`: continuidade de sessão validada e distinção entre falha de leitura e resultado incerto de ação.

## Impact

Extensão solicitada pelo proprietário em 12/10/2026: aplicar aos clientes os mesmos critérios de cor já aprovados para fotógrafos. Base da extensão: develop f942cf3, com PR #160 publicado e validado; detalhes da validação e limites em validation.md. Sem alteração de autenticação ou coleta.

Frontend, testes e documentação. Sem mudança de autenticação backend, lifetime, grants, permissões ou sessões reais. Solicitação humana autoriza implementar estes ajustes. A implementação original partiu de develop 0292e2d e preservou alterações posteriores do motor facial; os snapshots históricos do servidor e a validação posterior de f942cf3 constam em validation.md. O registro local preexistente de localização/e-mail permanece preservado fora dos commits desta change. Sem servidor local, carga, dados reais de teste ou configurações/segredos. PR/CI/deploy conforme autorização vigente, pausando durante CI.
