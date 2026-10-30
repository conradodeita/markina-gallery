# Proposal

## Why

O inventário somente-leitura de produção identificou dados biométricos cifrados vinculados ao `APP_ENV` de origem. A change `transition-app-env-bound-integrations` corretamente bloqueia a transição enquanto esses dados não tiverem tratamento próprio; esta proposta define uma análise e um caminho seguro para os dados comprovadamente elegíveis, sem habilitar busca facial ou pagamentos reais.

## What Changes

- Inventariar somente metadados agregados e categorias dos dados biométricos cifrados vinculados ao ambiente, sem abrir payloads, expor IDs, caminhos ou valores de clientes.
- Definir critérios verificáveis de elegibilidade com base em origem, finalidade, consentimento aplicável, retenção e autorização para o ambiente de destino. Dados desconhecidos ou inelegíveis continuam bloqueando a transição.
- Especificar e testar, com dados sintéticos, a re-cifragem explícita e atômica dos objetos elegíveis entre contextos ambientais, preservando vínculos, consentimentos, auditoria e recuperação.
- Exigir backup cifrado verificável, fingerprint estável, plano operacional revisável e aprovação humana específica antes de qualquer operação real.
- Manter indisponível o processamento facial em produção durante e após esta mudança; não excluir, reclassificar nem migrar automaticamente dados, e manter fechado o gate de pagamentos reais.

## Capabilities

### New Capabilities

- `privacy-biometric/environment-bound-ciphertexts`: classificar e, somente quando elegível e explicitamente aprovado, migrar objetos biométricos cifrados entre contextos de ambiente preservando privacidade e isolamento por tenant.

### Modified Capabilities

Nenhuma. A change de transição APP_ENV mantém seu bloqueio até que esta operação independente seja concluída e uma nova coleta prove que não restam objetos biométricos vinculados à origem.

## Impact

A implementação futura poderá envolver os contextos criptográficos, os armazenamentos de referências, embeddings, localizadores, notificações e jobs faciais, além dos procedimentos de inventário, backup e recuperação. As superfícies exatas deverão ser confirmadas por inspeção do código antes da implementação. Não altera APIs de cliente, consentimentos existentes, retenção, modelos, flags de busca facial, credenciais de pagamento, pedidos, PIX ou o gate `MERCADOPAGO_ALLOW_LIVE_PAYMENTS`. Esta proposta não autoriza ler payloads biométricos nem modificar dados ou serviços de produção.
