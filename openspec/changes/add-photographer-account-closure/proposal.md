# Proposal

## Why

O fotógrafo pode querer encerrar a conta, mas hoje o tenant só distingue `active` e `suspended`, e a minuta atual direciona o pedido ao suporte. Suspensão não é encerramento: fechar a conta sem um fluxo próprio pode interromper pedidos em andamento, enquanto apagar os dados imediatamente pode prejudicar entregas, pagamentos e obrigações ainda abertas.

## What Changes

- Criar um fluxo autenticado de solicitação e conclusão de encerramento, com estado próprio, bloqueio de novas galerias e uploads e acesso limitado para resolver o que já foi iniciado.
- Manter galerias publicadas utilizáveis pelos clientes dentro dos prazos apresentados, permitindo finalizar seleções/compras e concluir os pedidos existentes antes do fechamento definitivo.
- Permitir o encerramento com avisos push ou WhatsApp já enfileirados; enquanto a conta estiver encerrada, eles permanecem na fila sem envio.
- No encerramento, arquivar diretamente pastas comprovadamente nunca liberadas aos clientes, sem espera de trinta dias, após conferir pedidos, obrigações, processamento e integridade; pastas já liberadas seguem seus prazos.
- Arquivar capa isolada de galeria sem pasta de fotos em unidade técnica recuperável junto da conta, sem taxa adicional; havendo fotos, manter a capa com a última pasta ativa.
- Após prazos de galerias, pedidos e demais obrigações serem concluídos, encerrar o acesso do Tenant; o fotógrafo não poderá fazer login enquanto a conta estiver encerrada nem reativá-la por fluxo normal.
- Não oferecer estorno manual de créditos comprados. Créditos, compras, transações e demais registros leves permanecem no PostgreSQL após o encerramento.
- Arquivar os arquivos de mídia de grande volume pelo fluxo existente de arquivo frio por pasta, sem criar um segundo pacote de banco. Dez anos após o encerramento inicia revisão manual pelo proprietário; não há expurgo automático, e a mídia permanece recuperável enquanto não for explicitamente removida por fluxo auditado.
- Permitir que o `PlatformOwner` solicite, por ação simples e auditada, a recuperação dos arquivos arquivados do Tenant enquanto existirem e não tiverem sido explicitamente removidos; após pull íntegro, o proprietário poderá reabrir o acesso do Tenant.
- Manter dados técnicos de encerramento, estado e nome/e-mail mínimos sob acesso restrito no PostgreSQL para permitir restauração pelo proprietário; o décimo aniversário inicia revisão manual, sem expurgo automático dessas identidades. Compras, transações e protocolo de aceite permanecem segundo suas políticas próprias. Para reabertura posterior, o fotógrafo confirma a identidade por CPF e fornece dados atuais; somente a impressão protegida, versionada e não reversível do CPF permanece enquanto houver mídia recuperável, sendo removida com a mídia. Mídia biométrica permanece fora do arquivo frio. Ao concluir o encerramento, apagar os dados biométricos operacionais após parar buscas pendentes, preservando apenas prova mínima de consentimento e auditoria; após reabertura, índices só são reconstruídos pelo fluxo vigente de consentimento. Segredos de autenticação não são exportados.
- Incluir nos Termos versionados uma seção própria de Aviso de Privacidade no mesmo documento e aceite, com explicação direta do encerramento, das galerias já publicadas, das obrigações pendentes, da possibilidade de recuperação pelo proprietário e das categorias de dados preservadas ou apagadas; informar que a revisão manual aos dez anos não apaga automaticamente a mídia, sem expor provedor ou mecanismos internos de armazenamento.
- Mostrar `Encerrado` no diretório e no detalhe do tenant no console do `PlatformOwner`, claramente distinto de `Suspenso`, com origem, data da transição, contador de dias encerrados e sinalização de revisão manual ao completar dez anos, além da trilha de auditoria.
- Não iniciar expurgo automático de fotos no arquivo frio, inclusive ao completar dez anos; exclusão de mídia seguirá o fluxo explícito e auditado aplicável após revisão do proprietário.

## Capabilities

### New Capabilities

- `photographer-account-lifecycle`: solicitação, encerramento gradual, verificação de pendências e tratamento dos dados operacionais da conta do fotógrafo.

### Modified Capabilities

- `photographer-onboarding`: explicar o encerramento no texto versionado mostrado ao fotógrafo antes do aceite e preservar o vínculo com o protocolo de aceite existente.
- `platform-admin/owner-console`: exibição e auditoria do estado `Encerrado` no diretório e no detalhe do tenant, sem confundi-lo com suspensão.

## Impact

Afeta o modelo e as rotas de lifecycle do tenant no backend, os gates de novas galerias/uploads, a preservação de acesso às galerias já publicadas e a conciliação de operações já iniciadas, o painel do fotógrafo, o console do proprietário, migrations e testes. A change é local; não autoriza migration, publicação ou alteração em produção.
