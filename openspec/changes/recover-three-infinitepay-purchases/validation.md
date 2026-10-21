# Evidências e continuidade — 21/10/2026

## Autorização e fronteiras

O titular afirmou ausência de vendas/pagamentos/histórico de tentativas no painel e, após esclarecimento de que isso não comprova invalidação remota, determinou: “Isso não é necessário! Prossiga sem essa confirmação”. Essa decisão substitui a pré-condição externa somente para os três alvos desta operação. A origem da decisão continua sendo o titular; não foi obtida confirmação da InfinitePay e a ferramenta não a simula. Risco residual: uma URL antiga ainda pode ser paga, inclusive depois de um PIX. Não alterar política geral nem afirmar cancelamento remoto.

## Implementação e validação local

Ferramenta em backend/operations/recover_three_infinitepay_purchases.py, sem import/rota no produto. Base main publicada 5446cf4d; branch codex/recover-three-infinitepay-purchases. Não depende da publicação do PR #263. Nenhuma alteração em dependências, schema, serviços, credenciais, PR #261 ou PR #262.

- Primeiro ensaio SQLite: 9 aprovados, 2 ignorados e uma falha de consulta ambígua no próprio teste de snapshot; join corrigido com a FK explícita.
- Ensaio SQLite intermediário: 12 aprovados, 2 ignorados, 20 avisos em 119,21 s. Posteriormente foram acrescidos guardas de quantidade/cliente, lock compatível com FK e cenários CLI/inelegibilidade.
- Primeiro PostgreSQL: 13 aprovados e uma falha de deadlock na corrida com confirmação. A causa foi reproduzida: Tenant FOR UPDATE bloqueia KEY SHARE da FK do recibo enquanto o confirmador mantém Client. Operação ajustada para Tenant FOR NO KEY UPDATE, mantendo Client/pagamentos ordenados. Nenhuma modificação no helper global do app.
- Regressões de concorrência após correção: 4 aprovadas, 12 desmarcadas, 6 avisos em 32,62 s, incluindo três corridas com confirmação.
- **Matriz final PostgreSQL: 21 aprovados, 6 avisos, em 182,51 s.** Inclui preservação de snapshots, PIX válido, seleção nova preservada, simulação sem persistência, recusas actor/escopo/cliente/fundos/snapshot/fingerprint/PIX/prazo, pré-imagem, reexecução após nova compra, retorno tardio e concorrência. Nenhum checkout ou pagamento real foi criado.
- Ruff da ferramenta e testes: aprovado. OpenSpec estrito da change: aprovado. Testes de CLI comprovam recusa antes do banco se faltam fingerprint, reconhecimento do risco ou runtime inventariado.

Revisão proporcional: _restore_local_selection não é reaproveitada porque desfaz associações históricas; a ferramenta conserva essas associações e usa prepare_group/cart_payload para validar o caminho real do PIX. Nenhum código funcional obsoleto foi encontrado cuja remoção fosse necessária neste recorte. Não foi iniciada refatoração geral.

## Inventário Oracle somente leitura

Projeto Compose markina-gallery, domínio https://markina.pickyourpic.com.br, proxy próprio em 127.0.0.1:8080; API 8000/tcp e web 3000/tcp internos. Quinze serviços próprios saudáveis. Não foram inspecionados/modificados recursos de outros projetos.

API: APP_VERSION=5446cf4d7328ef6283ebfab50b5d1976d561fc8d, APP_ENV=staging, imagem sha256:1eecc29b45863932f64b38bb38ca8da3428da62797f4bd63109bdcd937c06d2f. Administrador validado na associação ativa do tenant: f4606e36-a74c-4b31-b123-9ee2059412e5.

Compra preservada 04381887: confirmed, 11200 centavos. Digest financeiro antes da operação: 105dd322d3b5f9f3f37ea226f6a5600cee7d04c1b422ccbfd40b30d0371ace7e. O digest abrange compra, transação, estados/valores congelados dos pedidos e itens, sem publicar o NSU ou a URL.

## Simulação remota concluída; aplicação pendente

PR draft #264 criado e anexado ao chat, independente dos PRs #261/#262/#263. Candidato funcional inicial 527145f4f3e076eb46d9e387b93d846a6d462fc4; ferramenta validada SHA256 515d12b556e0946fd6c63aaed0f8ebad72909ca2f82ed55ca76f57ac438778b3. A ferramenta foi transmitida por stdin, com hash e identidade da imagem conferidos, sem instalar código no app ou trocar serviço.

Simulação real com rollback aprovada. Fingerprint da pré-imagem: eb2a38b3d3c5e746fafa988498271a36f334573f9d988e8dd5107c7b86bcaed0. Arquivos no servidor: /var/lib/markina-gallery/deploy-state/owner-recovery-20261021/before-v1.json e dry-run-v1.json, ambos 0600 em diretório 0700. Cópia temporária do código removida ao final. Nenhuma chamada de criação/consulta/cancelamento foi feita à InfinitePay.

| Compra original | Fotos restauradas | Total de fotos no carrinho | Total atual |
|---|---:|---:|---:|
| eae11005 | 22 | 22 | 15400 centavos |
| e2194ce5 | 1 | 4 | 20 centavos |
| 11f18369 | 1 | 24 | 1510 centavos |

Os carrinhos preservam 26 seleções novas já existentes, além das 24 fotos a restaurar. PIX válido nos três. Cartão indisponível porque a configuração ativa está card_enabled=false, versão 5; API Key configurada. Não habilitar cartão nem alterar essa configuração por esta operação.

Leitura após rollback: estados/revisões originais preservados (eae awaiting_payment/rev2; demais verification_required/rev1), zero eventos persistidos de owner_recovery e 26 seleções existentes. Digest financeiro de 04381887 continuou 105dd322d3b5f9f3f37ea226f6a5600cee7d04c1b422ccbfd40b30d0371ace7e. As referências de grupo PIX no relatório dry-run não foram persistidas e não são links de pagamento reais.

Próximo gate: CI pertinente do candidato aprovado, seguido de aplicação atômica autorizada com pré-imagem/fingerprint atuais e conferência posterior. Se qualquer dado mudar, refazer simulação em novo arquivo antes de aplicar. A pré-imagem é um manifesto minimizado para auditoria, não promessa de rollback financeiro automático após a cliente acessar/pagar PIX. O CI final por SHA/run SHALL ser registrado no corpo do PR #264; nunca tratar jobs pendentes como aprovação. Ainda não houve aplicação na Oracle nesta revisão.

Antes da simulação, apresentar impacto: locks breves somente da conta/clientes/recursos relacionados e alterações não visíveis revertidas na transação. Na aplicação, recuperar somente os três alvos; sem restart, migration, troca de imagem, edição de .env ou nova chamada ao provedor. Para a cliente, retomada em /library/cart, com novas referências de pagamento local e histórico anterior conservado em exceção. Não prometer novo botão em Compras nem sucesso de criação de cartão de R$ 0,05, cujo HTTP 422 continua sem causa demonstrada.
