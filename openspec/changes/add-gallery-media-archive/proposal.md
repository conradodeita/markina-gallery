# Proposal

## Why

Pastas expiradas continuam ocupando o disco local, enquanto remover a mídia pode romper seleções e pedidos existentes. O arquivo frio precisa liberar armazenamento sem apagar referências dos clientes e sem cobrar recuperação que não concluiu.

## What Changes

- Arquivar mídias por pasta pública ou privada após a expiração e 30 dias completos, mesmo com carrinhos/seleções em aberto; pedidos comerciais em aberto continuam bloqueando.
- Encerrar o prazo por galeria para novas pastas: pastas legadas em produção começam indeterminadas até o proprietário configurar prazo; novas pastas exigem prazo finito independente no momento da liberação.
- Atualizar o painel do fotógrafo para configurar o prazo por pasta e exibir ao cliente o prazo daquela pasta.
- Manter atualizados os rótulos de expiração nas telas administrativas enquanto permanecem abertas, sem exigir recarga manual ao vencer um prazo.
- Permitir ao fotógrafo renovar diretamente uma pasta pública expirada, sem solicitação do cliente, informando dias contados do salvamento e beneficiando todos os clientes já autorizados. A renovação normal exige mídia local disponível e ocorre somente nos 30 dias após o vencimento efetivo; não altera a reabertura individual das pastas privadas nem substitui recuperação fria.
- Na área Vendas e pagamentos, mostrar em cada solicitação de reabertura se o prazo valerá para todas as clientes autorizadas da pasta pública ou somente para a cliente solicitante da pasta privada; solicitações legadas sem pasta não oferecem aprovação por esse fluxo.
- Explicar no momento da configuração que a pasta entra em arquivo 30 dias após expirar e que recuperar exige a taxa vigente em créditos, definida pelo proprietário.
- Incluir a regra de expiração e recuperação nos Termos operacionais que o tenant aceita, preservando o texto/versão/hash no protocolo de aceite existente.
- Manter as referências da seleção, permitir prévias protegidas somente das fotos selecionadas antes do vencimento durante a janela de 30 dias e ocultar toda a mídia quando arquivada. Navegação da pasta e novas seleções continuam bloqueadas após o vencimento; pedidos comerciais em aberto continuam bloqueando o arquivo.
- Automatizar a recuperação por solicitação do tenant, prazo escolhido e taxa global fixa em créditos por pasta/ciclo; reservar créditos, debitar só após pull completo/verificado e liberar a reserva em falha.
- Isentar o proprietário no seu próprio fluxo; permitir retry manual pelo proprietário após falha para um tenant, aplicando a taxa somente no sucesso.
- Mostrar operação e ledger no card/histórico do tenant e permitir ao proprietário consultar logs técnicos sanitizados.
- Preservar cópia primária até verificar que a cópia fria pode ser recuperada; manter a exclusão explícita como fluxo separado.
- Remover cópia fria somente mediante solicitação explícita validada e operação auditada, confirmada antes de concluir; não haverá expurgo automático por idade ou encerramento de conta na primeira versão.
- Definir a política de retenção final em change futura.
- Fazer a configuração e o teste reais do Drive somente depois da entrada autorizada do sistema em produção, começando pelo proprietário como fotógrafo; os demais tenants só recebem sinal verde depois que o fluxo real de arquivo e recuperação passar.

## Capabilities

### New Capabilities

- `media-storage/gallery-media-archive`: ciclo de arquivamento e recuperação de mídia por pasta, preservando seleção e histórico comercial.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: os cartões de reabertura exibem o alcance específico antes da decisão e tratam solicitações antigas sem pasta associada sem oferecer uma aprovação que a API rejeitaria.

## Impact

- Novos estados persistentes e jobs retomáveis para elegibilidade, transferência, verificação, recuperação e falha.
- Integração com as pastas/fotos, seleções, pedidos, créditos, card do tenant e painel do proprietário.
- Google Drive como armazenamento frio privado; a identidade e a raiz próprias para mídia permanecem separadas do backup do banco. O tenant do proprietário terá a mesma cobertura de arquivo e recuperação dos demais, com sua isenção de créditos já aprovada.
- A implementação local usa storage e transporte sintéticos. O adaptador de mídia para Drive pode ser desenvolvido e validado por testes com transporte HTTP sintético, sem credenciais reais nem chamadas de rede; sua configuração e operação real ficam para depois da entrada autorizada em produção, num primeiro estágio restrito ao proprietário. Os tenants permanecem bloqueados até o teste passar. Nenhuma chamada real, migration, remoção física ou alteração de produção é autorizada por esta etapa local.
