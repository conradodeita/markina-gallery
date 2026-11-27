## Decisions

1. Usar um PostgreSQL descartável e duas contas fictícias. Começar a prova global com uma exportação consistente e medir a recuperação. Avaliar pgBackRest se a recuperação diária ou o tempo medido forem insuficientes.
2. Provar um repositório cifrado Restic com chave recuperável fora do ambiente simulado de origem. Medir a transferência via Rclone quando o destino de ensaio comportar sua autorização. Usar Backrest como painel opcional do operador.
3. Restaurar a cópia global em banco isolado e testar a seleção dos registros associados ao fotógrafo. Conferir relacionamentos, conflitos e ausência dos dados do segundo fotógrafo antes de considerar uma recuperação individual.
4. A mesma solução aberta SHALL participar da prova global e da prova de arquivo/recuperação fria. Reusar o contrato, catálogo, fila, UI e validação de tamanho/SHA-256 de `add-gallery-media-archive`; comparar Restic e Rclone com o contrato de objeto por pasta/ciclo. O plano só será aceito se provar a restauração seletiva sem enfraquecer isolamento, integridade ou exclusão auditada.
5. Separar raízes, chaves, namespaces, retenção e autorização entre backup global e arquivo de mídia, mesmo que compartilhem ferramentas. Filtros de caminho são conveniência de recuperação, nunca autorização; o servidor valida tenant, ownership e catálogo antes de iniciar qualquer operação.
6. Tratar como parte obrigatória do piloto o ciclo comercial vigente: expiração da pasta, janela de 30 dias até elegibilidade e, conforme `fix-cold-recovery-access-window`, 30 dias fixos para novas recuperações do fotógrafo. Preservar taxa por pasta/ciclo, reserva idempotente, débito após disponibilização íntegra, liberação em falha e reconciliação sem débito quando o resultado for incerto. Proprietário permanece isento e não haverá expurgo automático.
7. Consolidar a evidência das três recuperações e dos contratos de prazo/crédito em uma única prova sintética antes de qualquer escolha operacional. Não duplicar nem substituir o billing ou o ciclo de vida do aplicativo pela ferramenta de backup.

## Decisão do proprietário em 27/11/2026

Manter a cópia PostgreSQL portátil entre ambientes compatíveis e validar a restauração em alvo isolado, inclusive no PC de desenvolvimento. A cópia externa, a chave e a configuração de acesso precisam ser recuperáveis independentemente do Oracle. O ensaio de reconstrução completa do SaaS em um servidor substituto fica para depois do lançamento comercial. A operação do novo backup segue em `add-open-source-global-postgresql-backup`.
