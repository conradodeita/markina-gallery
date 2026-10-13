## Operação no servidor

O registro em `main` contém somente a declaração de dispatch e um job inerte que recusa a execução; selecionar explicitamente `develop` para acessar a versão operacional revisada no PR #170. O GitHub exige que o caminho do workflow exista na branch padrão antes de permitir dispatch de outra ref. O registro não promove aplicação/scripts nem faz deploy. Não aprovar o deploy automático de um push somente para disponibilizar manutenção: o reset usa a imagem publicada e não precisa criar dump adicional.

Registro integrado pelo PR #171 na `main` como `e0b29dd97f4319d43e49870cefff114f993cd7b8`, após CI verde `38471017470`. A divergência entre a entrada inerte na `main` e a versão completa em `develop` é intencional: ao reconciliar branches, conservar a versão operacional em `develop`, sem substituí-la pelo registro.

Inventário validado: https://github.com/conradodeita/markina-gallery/actions/runs/38471222311 — ref `develop`, modo `owner-inventory`, proprietário `conradodeita@gmail.com`, SHA publicado esperado `0ef80fdf912e8f9cbde730d061b69b73d46ff5aa`, sem confirmação de execute. Concluiu com sucesso após aprovação humana do Environment `homolog`. Elegibilidade e topologia conferidas; contagens de exclusão e preservação estão em `tasks.md`. O manifesto continua exatamente 164 dumps/2.077.111.921 bytes. Não houve exclusão.

Primeira execução: https://github.com/conradodeita/markina-gallery/actions/runs/38472862716 — mesmo owner/ref/SHA, modo `owner-execute`, confirmação `RESET_HOMOLOG_TO_OWNER_AND_DELETE_164_DUMPS_WITHOUT_BACKUP`. Após gate humano, abortou antes da pausa/exclusão porque o usuário não pôde criar a pasta de retomada. Não houve commit de banco, limpeza de mídia/dumps ou estado pendente. Todos os serviços permanecem saudáveis. Não reexecutar o wrapper antigo: publicar a correção de prontidão/snapshot em `develop` e repetir inventory antes do próximo execute protegido.

Prontidão do state: `/var/lib/markina-gallery/owner-reset` foi provisionado vazio em 13/10/2026 como ubuntu/ubuntu, modo 0700, após conferir caminho canônico sem symlink. Somente esse diretório foi criado por sudo; o pai permanece root/root 0755 e o diretório de dumps ubuntu/ubuntu 0700. Ambos os modos conferem owner/mode/path/permissões do state antes de pausar writers. O snapshot real do Docker confirmou `migrate|exited|none` e os três serviços Evolution `running|healthy`, sem erro de template.

Destino exclusivo: `/opt/markina-gallery`, projeto Compose `markina-gallery`, Nginx local `127.0.0.1:8080`, domínio canônico `https://markina.pickyourpic.com.br`. O operador escolhe `owner-inventory` ou `owner-execute` no workflow existente **Maintenance homolog**, ref `develop`, com e-mail proprietário e SHA efetivamente publicado. `owner-execute` exige `RESET_HOMOLOG_TO_OWNER_AND_DELETE_164_DUMPS_WITHOUT_BACKUP` e aprovação do Environment `homolog`.

O workflow encaminha somente código revisado de manutenção. A imagem API usada no contêiner efêmero precisa ser exatamente a imagem publicada; não há troca de checkout, deploy, migration, backup ou recriação de volume. Inventário apresenta somente contagens e elegibilidade, sem exportar configurações/PII/segredos.

Antes de execute, revisar o inventário novo, os itens preservados e a autorização registrada. Há uma breve pausa exclusiva da API/workers Markina. Evolution, banco, Redis, Nginx Proxy Manager e projetos vizinhos permanecem ativos. O wrapper compara IDs, imagens, início e estado dos três containers Evolution antes/depois. Todos os writers inventariados (incluindo RAW, preview e Gemma) precisam estar parados antes da exclusão.

## Falha e retomada

Se execute falhar, não declarar rollback. Os writers permanecem pausados e seus IDs originais ficam em `/var/lib/markina-gallery/owner-reset/pending.json`, junto do SHA/owner, sem dados de negócio. Inspecionar o resultado sanitizado e a fase (`preflight` ou `database_committed`). Para retomar, repetir o mesmo procedimento com o mesmo proprietário/SHA: as exclusões são idempotentes e as configurações já preservadas são novamente conferidas.

Nunca apagar o estado pendente para contornar uma divergência, iniciar novos writers ou restaurar banco automaticamente. Resolver a causa dentro do escopo antes de retomar. Após sucesso, somente os containers originalmente ativos são reiniciados e conferidos saudáveis; o estado pendente é removido.

## Itens preservados

Senha/TOTP/e-mail e identidade da conta proprietária; tenant/vínculo e sessões/push administrativos dessa conta; PIX/InfinityPay/canal WhatsApp/marca/notificações/tabelas de preço/processamento; privilégios e observabilidade global; dados/volumes e conexão Evolution; arquivos `.env` e segredos; snapshots de branding/configuração e todos os arquivos fora do conjunto autorizado de 164 `.dump`.

## Dados excluídos

Todas as tabelas operacionais de todas as contas, incluindo compras/pagamentos de teste e mídia de histórico, OTP/sessões/push de clientes, e-mails e filas técnicas pendentes; os demais admins/tenants/vínculos/concessões/preferências; auditoria operacional e de tenants excluídos; arquivos de source/derivatives/history/facial-references/raw-staging e ativos de marca fora do namespace/referências proprietários; e os 164 `.dump` antigos somente após confirmar o reset principal. Não há chamada externa para estornar ou apagar transações na InfinityPay.
