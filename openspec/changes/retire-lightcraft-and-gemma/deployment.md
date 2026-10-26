# Release de aposentadoria LightCraft/Gemma

## Autorização e limites

O proprietário autorizou em 26/10/2026 corrigir até merge e deploy bem-sucedido. CI verde, inventário atual, preparação das candidatas, preservação de dados e procedimento de recuperação são gates obrigatórios. Não há autorização para excluir histórico, tabelas, imagens ou volumes.

## Inventário inicial somente leitura — 26/10/2026

- Host `ubuntu@132.145.193.169` (`clearbudget-vnic`), projeto `markina-gallery`, raiz `/opt/markina-gallery`, checkout limpo em `f9091a7be60314285e2c19b762c62eb5b64183e5`.
- Entrada exclusiva Markina `127.0.0.1:8080`, domínio `https://markina.pickyourpic.com.br`. O runtime declara `APP_ENV=staging`; preservar esse valor e demais controles sem inferir equivalência com nome de GitHub Environment.
- Schema observado via transação somente leitura: `20261025_0089`. Nenhuma migration é necessária.
- API/worker: `sha256:f1715fb18dacbcf24e23bef75546729c9aeebc8ac2ade7c40c0f8aa5bb41ec49`; web: `sha256:4538c63e6beba1bcc7b926ccbcd27685b7ac05d47a524d8831c8a2e3be91b606`.
- SFace index/search/maintenance, preview adjustment, RAW e Gemma estão ativos e saudáveis. Banco, Redis, Nginx e Evolution também saudáveis. Imagens especializadas e overlays serão fixados na evidência de preparação imediatamente anterior ao rollout.
- RAW: nenhum job; uma configuração histórica habilitada em RawTherapee. Gemma: configuração desabilitada, 126 jobs cancelados e 86 concluídos; nenhum job facial pendente/processando. Prévia: 3.593 resultados `ready`. Estas são contagens históricas, não autorização para apagá-las.
- Configuração ativa tem overlays de branding, monitor, manutenção Pillow e duas publicações Orders; há override RAW ainda ativo. Os overlays e patches de segurança não podem ser perdidos na troca. Segredos não são impressos nem copiados ao Git.

## Plano de impacto zero — preparação pendente

1. Revalidar todas as filas/writers, capacidade, fontes/versões e integridade; preservar IDs das imagens e configuração anterior em estado operacional protegido do projeto.
2. Construir candidatas sem substituir containers, conferir dependências/modelos/configuração e smoke RawTherapee 5.13 ARM64. Preservar correções Pillow/HTTP e controles de pagamentos vigentes.
3. Confirmar CI verde e merge da PR. Usar lock de release Markina e manutenção com resposta recuperável; drenar writers pelo contrato de parada já existente. Exigir filas sem trabalho ativo e confirmar continuidade de callbacks.
4. Substituir exclusivamente os serviços de aplicação afetados, retirar somente os dois executores aposentados quando ociosos, preservar volumes/linhas históricas e o ambiente atual. Banco, Redis, Evolution, proxy externo, redes e portas não são recriados. O Nginx Markina só pode receber recarga testada para resolver upstreams após a troca.
5. Confirmar schema, saúde, versões/imagens, hashes/contagens de integridade e HTTPS antes de encerrar manutenção. Recuperação usa as imagens anteriores e schema 0089 compatível, sem restauração de banco.

O procedimento API/web genérico permanece bloqueado para esta mudança especializada: seu manifesto antigo espera schema 0087 e não inclui workers. Não flexibilizar essa classificação nem executar o release Orders pontual de outra revisão. O procedimento especializado exato ainda deve ser preparado e validado antes de qualquer mutação remota.
