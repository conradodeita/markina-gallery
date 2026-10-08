# Tasks

## 1. Prontidão e salvamento no backend

- [x] 1.1 Implementar decisão compartilhada de prontidão da capa configurada e projetá-la em Detalhes/editor; testar ausência, preparando, falha, pronta, asset removido e galeria/conta incompatível, registrando evidência e mantendo a etapa pendente até prévia pronta.
- [x] 1.2 Exigir prontidão antes de salvar campos visuais da etapa Detalhes no PATCH de settings; testar negativa sem alteração parcial/auditoria de sucesso e positiva com capa pronta; comprovar que criação, Ajustes, Vendas, organização e upload continuam possíveis sem capa.
- [x] 1.3 Documentar o contrato de prontidão e os limites da conclusão guiada; revisar testes existentes de capa/configuração multitenant e executar as regressões afetadas, sem abrir exceções à exigência para manter fixtures antigas.

## 2. Fluxo administrativo

- [x] 2.1 Exibir capa obrigatória e estados/ações de recuperação em Detalhes; bloquear salvar/avançar enquanto a API não comprovar prontidão; testar ausência, processamento, falha, carregamento e sucesso com o componente real e contrato do backend.
- [x] 2.2 Revalidar a prontidão no backend ao acionar Concluir antes de navegar ao resumo; testar navegação direta às etapas finais, estado antigo, consulta falha e conclusão com capa pronta, sem criar estado persistente de publicação.
- [x] 2.3 Validar a retomada de galeria existente sem capa e o retorno a pendente após remoção/substituição; comprovar manutenção dos dados/vínculos e ausência de revogação automática; registrar QA mobile/desktop proporcional ao formulário alterado.

## 3. Integração e entrega

- [x] 3.1 Executar testes backend/frontend pertinentes, Ruff, lint, typecheck, build, OpenSpec 1.14.0 estrito e diff-check; revisar o diff e registrar evidência no baseline atual antes de declarar pronto.
- [x] 3.2 Preparar commit/PR focado e anexar ao chat; acompanhar CI do HEAD entregue conforme preferência do proprietário. Não publicar sem inventário/plano/autorização específicos.

## 4. Refinamento editorial solicitado em 08/10/2026

- [x] 4.1 Retirar apenas o parágrafo explicativo indicado pelo proprietário em Detalhes, verificar a interface afetada e registrar evidência; preservar orientação de obrigatoriedade/prontidão e validações existentes.
- [ ] 4.2 Revisar diff focado, entregar PR e parar imediatamente após o push para aguardar o resultado do CI informado pelo proprietário. Merge/deploy e aceite remoto são posteriores.

## Workflow follow-up

Aplicação após revisão da proposta. Ensaio visual remoto após publicação autorizada. Sincronização/arquivamento apenas após revisão humana. Retomar piloto A+B em sua task 8.3 e preservar limpeza para o final; não incluir correção de Compras ou orientação OTP no mesmo commit desta change.
