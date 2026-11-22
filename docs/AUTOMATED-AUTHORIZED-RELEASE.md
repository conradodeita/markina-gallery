# Release 0090 com CI reutilizado

Este fluxo está em implementação e não substitui o runbook aprovado enquanto a mudança não estiver integrada e validada. A operação 0090 em andamento continua usando o workflow anterior e o SHA de suporte próprio.

Reconciliação de 27/10/2026: o preflight anterior terminou sem fingerprint e a correção de preservação foi integrada pela PR #306. A otimização pode ser integrada antes de iniciar uma nova instalação/preflight, após CI verde da base e do novo SHA. Toda operação subsequente usa o SHA integrado atual e recolhe inventário novo; não há reaproveitamento do inventário que falhou.

Após revisão e integração, `preview-migration-0090-authorized.yml` disponibiliza instalação do wrapper, inventário somente leitura e release 0090. Cada despacho consulta a CI de push da main para o SHA exato e exige a execução mais recente concluída com sucesso e todos os jobs esperados verdes. SHA diferente, CI pendente/falho, job ausente, erro de API ou paginação incompleta bloqueiam a operação. O CI do candidato de aplicação continua sendo conferido pelo inventário.

Quando não existir backup reconhecido, `preview-adjustment-migration-backup` prepara dump online0089 e manifesto em `deploy-state/preview-adjustment-backups`, com aprovação `production`. Esta operação valida os demais gates sob lock, não para serviços e não executa DDL; seu inventário com backup null jamais autoriza release. Depois dela execute o preflight normal, que exige verificar o arquivo, checksum, permissões e listagem pg_restore. A listagem não equivale a ensaio completo de restauração.

O manifesto consolidado efetivamente usado por API/web é conferido contra os config-hashes dos containers e usado na mesma ordem. Referências históricas dos serviços preservados, como o override RAW removido ainda presente nos rótulos do Nginx, ficam somente na proveniência do fingerprint e não são carregadas para publicar API/web.

O release exige confirmação de autorização vigente para o ambiente, escopo e impacto, além da revisão no environment `production`. O inventário é exibido no resumo antes da revisão e seu fingerprint é propagado à execução, que compara novamente o estado sob lock. Um executor autorizado pelo proprietário pode aprovar a revisão em nome dele; o workflow não autoaprova o environment. Uma autorização para uma operação não permite ampliar escopo, afetar outros projetos, remover recursos ou executar uma recuperação destrutiva não autorizada.

O procedimento mantém backup verificável, interrupção temporária da API, ausência de downgrade automático e verificações posteriores conforme [release 0090](RELEASE-PREVIEW-ADJUSTMENT-MIGRATION.md). CI e evidência de um SHA não substituem a validação de outro; não usar um run de PR como CI de push em main.
