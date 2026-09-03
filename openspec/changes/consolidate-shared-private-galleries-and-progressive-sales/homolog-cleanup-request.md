# Solicitação de limpeza de testes — 2026-09-03

## Solicitação inicial e autorização ampliada

Após retestar a desvinculação em homologação, o proprietário informou que a falha persiste e autorizou limpar diretamente os dados de teste do banco. A antiguidade dos registros é uma hipótese do proprietário, não uma causa técnica comprovada. Não houve execução destrutiva nesta inspeção.

Na sequência, o proprietário autorizou explicitamente a limpeza completa, mantendo apenas administrador, configurações e pareamento WhatsApp. O escopo agora inclui o grafo operacional de testes, mídia e filas exclusivas da Markina, pelo pipeline existente com backup lógico e pausa restrita de API/worker. Foi informado que o dump não recupera os JPEGs excluídos. Essa autorização resolve o bloqueio inicial abaixo; não permite atuar em outros projetos nem modificar credenciais.

Também autorizou simular após a limpeza o fluxo em homologação com galeria, pasta, fotos e cliente sintéticos, incluindo vincular e desvincular. O teste deverá distinguir início da operação, processamento assíncrono e conclusão refletida na UI. Não modificar a política comercial nem prometer conclusão instantânea sem evidência; manter a confirmação de ação crítica exigida pelas diretrizes.

## Evidência disponível

- Código publicado: `5f2236ec80256ce53d5d8f1e5e5aed36c313b8b8`; `develop` local/remoto conhecido: `dd29ed6b6ccee882ce4c91012d1a357fd0330ed7` (diferença documental).
- Último inventário observado: run `33776335838`, job `100719691676`, em `2026-09-03T16:07:37Z`. Esse inventário antecede a nova solicitação e não substitui uma conferência atual antes da exclusão.
- Banco: 2 clientes, 1 Galeria pública, 1 privada, 2 vínculos públicos, 1 membro privado, 8 fotos, 4 seleções, 0 pedidos, 0 comunicações de pagamento, 1 sessão de cliente, 3 desafios OTP, 5 entregas WhatsApp e 1 operação de lifecycle.
- Mídia: 8 arquivos-fonte (5.266.451 bytes), 24 derivados (6.761.656 bytes) e nenhum arquivo histórico.
- Ausência de pedidos nesse inventário impede atribuir a falha reportada automaticamente ao caminho de materialização de compras confirmadas corrigido na task 8.7.18. É necessário preservar a evidência da falha antes de eliminar registros; limpar testes não comprova correção do defeito.

## Rotina existente e diferença de escopo

`scripts/maintain-homolog-data.sh` e `app.homolog_cleanup` não oferecem modo de execução limitado ao banco. A execução existente também remove arquivos de mídia, limpa o Redis exclusivo e pausa temporariamente API/worker. As raízes `parent_gallery` e `client` são truncadas com dependências, incluindo histórico comercial de teste quando existir; a operação não é uma desvinculação normal de produto.

A rotina preserva administrador, configurações e recursos/pareamento Evolution. Cria backup lógico antes da exclusão; esse dump não constitui backup dos JPEGs que a rotina também apaga. Não deve ser executada como se fosse uma operação somente de banco.

## Acesso e bloqueio operacional

- Tentativa de acionar `maintenance-homolog.yml` em modo `inventory` para `develop` recebeu HTTP 404: o workflow não existe na branch padrão registrada pelo GitHub. Nenhuma execução remota foi criada.
- O acesso automatizado está configurado no Environment GitHub; não há alias SSH local configurado. A documentação de implantação registra que o acesso SSH local anterior não era aceito. Não foram lidos, exportados ou alterados segredos.
- O mecanismo já existente no CI permite inventário e execução sinalizada por trailer específico, mas implica acionar o pipeline controlado de homologação. Não foi criado commit com sinalização destrutiva, não houve push, aprovação de Environment, alteração da branch padrão ou tentativa de contornar os controles.
- Bloqueio inicial resolvido pela autorização ampliada acima. Usar somente o pipeline já existente; a indisponibilidade do workflow separado não autoriza alterar a branch padrão nem contornar o Environment.

## Plano autorizado

Alvo exclusivo: projeto `markina-gallery`, diretório `/opt/markina-gallery`, entrada `127.0.0.1:8080`, subdomínio `markina-homolog.duckdns.org`. Apresentar inventário atualizado, preservar diagnóstico sanitizado da operação falha e criar/verificar backup lógico antes da exclusão. Se a limpeza completa for autorizada, explicitar que os arquivos de fotos também serão removidos e não são recuperáveis apenas pelo dump do banco. Ao terminar, conferir contagens, preservação administrativa/configurações, head `20260903_0042` e `/healthz`/`/api/health`, sem `down`, prune ou alteração de recursos de terceiros.

## Execução em andamento

- Inventário atualizado: solicitada reexecução somente do job de deployment do run `33776335838`, no mesmo SHA funcional já publicado `5f2236e`, sem trailer de limpeza. Environment aprovado para essa finalidade; deployment `6248283016`. Não há mudança funcional nem migration nova.
- A reexecução concluiu com sucesso (job `100729529116`). Inventário em `2026-09-03T16:36:23Z`: 2 clientes, 1 pública, 1 privada, 2 vínculos públicos, 1 membro privado, 8 fotos, 4 seleções, 0 pedidos/comunicações de pagamento, 1 sessão de cliente, 3 OTPs, 5 entregas WhatsApp e 1 operação lifecycle. Mídia: 8 fontes/5.266.451 bytes, 24 derivados/6.761.656 bytes, histórico vazio. As contagens continuam dentro do escopo de testes autorizado. Os nove serviços Markina/Evolution estão saudáveis e somente nginx publica `127.0.0.1:8080`.
- A limpeza será sinalizada em integração separada, somente após esse inventário. A evidência original da operação falha permanece no backup pré-limpeza; não será exposto conteúdo pessoal nem segredo nos logs/documentos.
- Tasks de acompanhamento: `8.7.20` (limpeza) e `8.7.21` (simulação autorizada). A revisão humana geral e o arquivamento continuam pendentes.
- A navegação administrativa no único navegador disponível retornou acesso indisponível por sessão ausente. O login foi aberto para autenticação humana, sem leitura de cookies/senhas ou criação de sessão artificial; isso não bloqueia a limpeza via Environment.
