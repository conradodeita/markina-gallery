# Tasks

## 1. Confirmar e documentar os gates existentes

- [x] 1.1 Conferir no código e nos testes que a conta live exige gate global ativo, configuração Mercado Pago ativa no tenant e credenciais com recebedor validado; executar somente os testes focados já existentes para esse contrato e registrar evidência. Evidência local em `validation.md`: 39 aprovados, 2 skips existentes.
- [x] 1.2 Conferir que conta de teste em ambiente operacional continua limitada ao par tenant/cliente e que retirar a permissão bloqueia novas emissões, mas preserva consulta e reconciliação; registrar evidência sem enviar pagamentos. Cobertura dos testes de operações/checkout; sem emissão externa.
- [x] 1.3 Reconciliar a documentação histórica do piloto para deixar claro que a restrição de cobrança real foi substituída por esta liberação, preservando as evidências e os resultados sandbox anteriores. Nota datada adicionada ao design e plano de release Orders.

## 2. Preparar e ativar a liberação geral

- [ ] 2.1 Preparar um plano operacional atual com SHA, serviços e portas, valor alvo do gate, matriz de tenants/configurações habilitadas e recuperação; apresentar o plano antes de alterar produção e verificar que não contém credenciais. O preflight 0090 corrigido confirmou o schema, mas falhou com `checkout_nao_e_main`: a produção mantém o checkout do SHA de produto publicado, enquanto o script de inventário, baixado e validado pelo hash do commit atual de `main`, exige que o checkout remoto seja o próprio `main`. Ajustar o inventário somente leitura para aceitar checkout de produção limpo e ancestral do SHA candidato atual, sem usar módulos Python locais não fixados; executar CI, instalar apenas o wrapper protegido e gerar o inventário atual antes de concluir esta task.
- [ ] 2.2 Após aprovação explícita do plano, ativar o gate de produção pelo fluxo operacional autorizado e verificar saúde local, HTTPS e estado do gate sem enviar cobranças reais de teste.
- [ ] 2.3 Confirmar a disponibilidade por fotógrafo com leitura somente de configuração/estado: contas próprias válidas habilitadas, tenants sem configuração ainda sem Mercado Pago, restrição de teste preservada e PIX inalterado; registrar evidências e manter a change ativa para revisão humana.
