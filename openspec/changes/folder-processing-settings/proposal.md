# Proposal

## Why

Lotes diferentes da mesma galeria podem exigir exposição e tratamento distintos. Hoje os painéis da etapa Imagens controlam a galeria inteira e não aparecem no Acervo da cliente, apesar de as pastas restritas usarem o mesmo processamento.

## What Changes

- Adicionar configuração de processamento por pasta de conteúdo, comum ou restrita, com herança inicial do padrão da galeria.
- No ajuste de prévias, escolher herdar, personalizar ou desligar; a configuração própria substitui integralmente o padrão, sem somar exposição/intensidade. Todo resultado parte da prévia convencional limpa.
- No reconhecimento facial, escolher herdar, permitir processamento ou pausar novos trabalhos na pasta, sempre subordinado aos gates existentes. A pausa não apaga índices nem retira automaticamente resultados já autorizados de busca.
- Oferecer progresso e ações limitadas à pasta; manter o resumo/padrão geral na etapa Imagens.
- Reutilizar um painel recolhível consistente em pastas comuns e no Acervo, com estados explícitos, indicadores de progresso, controles mobile e mensagens de sucesso/erro.
- Manter configurações atuais, permissões, JPEGs, derivados convencionais, histórico comercial, consentimento, retenção e política facial existentes.

## Capabilities

### New Capabilities

- `media-storage/folder-processing`: herança e substituição de configuração, escopo de ações, controle facial local e interface administrativa de processamento por pasta.

### Modified Capabilities

Nenhuma exigência consolidada é removida; a nova capacidade complementa os derivados protegidos e a audiência de pastas existentes.

## Impact

Modelos/migration aditiva, resolução e worker de ajuste, agendamento/status facial, APIs administrativas e controles React/CSS. Sem novo motor, dependência ou mudança em permissões de cliente. Não executar processamento de dados reais ou alterações de servidor durante a implementação local. Publicação exige o fluxo autorizado com inventário e plano de impacto. A evidência local pendente da change anterior será preservada e não incluída no commit desta change.
