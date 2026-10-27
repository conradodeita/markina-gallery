# Release 0090 com CI reutilizado

Este fluxo está em implementação e não substitui o runbook aprovado enquanto a mudança não estiver integrada e validada. A operação 0090 em andamento continua usando o workflow anterior e o SHA de suporte próprio.

Após revisão e integração, `preview-migration-0090-authorized.yml` disponibiliza instalação do wrapper, inventário somente leitura e release 0090. Cada despacho consulta a CI de push da main para o SHA exato e exige a execução mais recente concluída com sucesso e todos os jobs esperados verdes. SHA diferente, CI pendente/falho, job ausente, erro de API ou paginação incompleta bloqueiam a operação. O CI do candidato de aplicação continua sendo conferido pelo inventário.

O release exige confirmação de autorização vigente para o ambiente, escopo e impacto, além da revisão no environment `production`. O inventário é exibido no resumo antes da revisão e seu fingerprint é propagado à execução, que compara novamente o estado sob lock. Um executor autorizado pelo proprietário pode aprovar a revisão em nome dele; o workflow não autoaprova o environment. Uma autorização para uma operação não permite ampliar escopo, afetar outros projetos, remover recursos ou executar uma recuperação destrutiva não autorizada.

O procedimento mantém backup verificável, interrupção temporária da API, ausência de downgrade automático e verificações posteriores conforme [release 0090](RELEASE-PREVIEW-ADJUSTMENT-MIGRATION.md). CI e evidência de um SHA não substituem a validação de outro; não usar um run de PR como CI de push em main.
