# Minuta de política para decisão do proprietário

> **REGISTRO HISTÓRICO — desenho de runtime próprio aposentado em 25/11/2026.** Este arquivo preserva a aprovação e as discussões da proposta anterior, mas suas decisões de destino e implementação — inclusive Google Workspace — não são configuração operacional atual. Valores de cadência, RPO/RTO e retenção também devem ser confirmados nas especificações vigentes antes de orientar o novo desenho. Nada aqui autoriza operação em produção.

## Status

**Política inicial aprovada pelo proprietário em 06/11/2026.** O proprietário aprovou o escopo inicial e, após esclarecer que os valores se aplicam ao backup global de todos os tenants, respondeu “Aprovo para o backup global”. O pacote abaixo passa a orientar desenho e implementação local; não autoriza publicação, alteração do job existente, backup real novo, expurgo ou restore em produção. O nome histórico deste arquivo foi preservado como localizador da decisão.

## Pacote inicial aprovado

| Tema | Decisão aprovada | Limite |
|---|---|---|
| Cadência | Uma cópia cifrada do PostgreSQL por dia, conforme roadmap. | Horário de produção ainda será planejado; job atual preservado. |
| RPO | Meta inicial de até 24 horas de perda de dados em desastre. | Depende de backup diário bem-sucedido; falha deve ser visível, nunca contada como sucesso. |
| RTO | Meta de recuperação do escopo aprovado em até 8 horas. | Ainda não medida; precisa ensaio, não é SLA prometido. |
| Retenção | 7 diários, 4 semanais e 3 mensais. | Política das cópias; não autoriza apagar dados do banco ativo. Nenhuma cópia elegível para expurgo sem outra independente restaurável. |
| Ensaio | Restauração mensal em ambiente descartável, além do primeiro ensaio de aceitação. | Implementação inicial usa dados sintéticos e não lê backups de cliente. |
| Escopo inicial | PostgreSQL completo, schema, metadata de versão/privilégios e configurações essenciais de recuperação cifradas. | O conjunto contém dados pessoais, financeiros e eventualmente biométricos do banco; aprovação precisa contemplar essas classes e secrets essenciais. |
| Fotos e demais arquivos | Arquivos JPEG-fonte, derivados, referências/índices biométricos e sessões WhatsApp aguardam política específica. | O escopo inicial não pode ser apresentado como recuperação integral da aplicação; não apagar origem/mídia nem alterar retenção desses arquivos. RAW permanece fora do produto. |
| Recuperação por tenant | Começar com recuperação global em ambiente isolado; restauração lógica por tenant permanece decisão/etapa própria. | Antes de aceitar esse recorte, reconciliar expressamente tasks e requisitos relacionados; não alegar recuperação individual implementada. |
| Chaves | Proprietário guarda material de recuperação offline, fora do host e da conta Drive; runtime usa configuração protegida do servidor. | Nunca guardar a única chave junto das cópias nem pedir o segredo no chat. Mecanismo técnico será desenhado após aprovação. |
| Cópia independente | Drive conforme roadmap e outra cópia externa com conta/credenciais independentes, destino a escolher. | Enquanto o segundo destino real não for escolhido, validar contrato com armazenamento sintético local e manter expurgo/publicação bloqueados; não inferir independência de pasta ou cópia no mesmo host. |

## Alcance da aprovação e pendências operacionais

1. Valores aprovados para a plataforma inteira: não são cotas ou conjuntos separados por fotógrafo.
2. Escopo inicial aprovado inclui banco completo e configurações essenciais cifradas; dados pessoais, financeiros e biométricos que já estejam no banco fazem parte do conjunto. Arquivos de fotos/biometria/WhatsApp aguardam etapa própria.
3. Recuperação inicial é global; restauração lógica por tenant fica explicitamente para etapa posterior.
4. Custódia offline do proprietário e segunda cópia externa com credenciais independentes aprovadas. Google Workspace foi escolhido; identidade dedicada para rotina e conta do proprietário somente no ensaio pré-abertura. Quota, destino/permissões reais e custódia operacional ainda bloqueiam chamada externa/publicação/expurgo, mas permitem implementar e ensaiar contratos locais com armazenamento sintético.

O faseamento foi expressamente aprovado e deve ser refletido em proposal/design/specs/tasks antes do código. A implementação local pode avançar nas partes aprovadas e independentes; credenciais reais e destino externo indisponível não serão simulados como integração produtiva concluída.

## Preservação operacional

O serviço de produção existente, sua agenda e todos os objetos atuais permanecem sob autorização operacional própria. A entrada extra observada no ClearBudget não faz parte da implementação SaaS e não será removida automaticamente. A nova solução não reutilizará cópias legadas como conjuntos novos sem origem, schema, integridade e restore comprovados.
