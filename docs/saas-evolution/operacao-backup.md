# Backup e recuperação do Pick-your-Pic

> **Rotina aposentada em 25/11/2026.** Os passos de cifragem, agendamento e restauração desta página descrevem a engine própria que foi encerrada; não os use para operar o host. A prova open source substituta está em [`prove-open-source-backup-and-recovery`](../../openspec/changes/prove-open-source-backup-and-recovery/proposal.md). A recuperação de pastas frias por fotógrafo continua como fluxo de produto separado no aplicativo e deverá integrar a mesma ferramenta na prova, preservando seu billing e seus prazos.

## Disponibilidade

O release do SaaS já teve um dump operacional restaurado em PostgreSQL isolado. A fundação inclui empacotamento cifrado, catálogo e agenda diária. O ensaio sintético confirmou upload, download e restauração pelo Drive. O proprietário escolheu a mesma conta Workspace para a rotina e o app criou a pasta privada `Pick-your-Pic Tenants` na raiz do Meu Drive. A rotina ainda depende de chave protegida, vínculo operacional e instalação e verificação do agendador. [Recibo do ensaio](../../openspec/changes/add-platform-backup-recovery/drive-restore-proof.md) · [Destino](../../openspec/changes/add-google-drive-storage-foundation/production-drive-proof.md#destino-da-rotina-verificado).

## Como será a rotina automática

1. Na execução diária, o agendador coordena a geração de um dump consistente do PostgreSQL e reúne as configurações essenciais previstas. O pacote é global e inclui as informações dos tenants presentes no banco. Arquivos de fotos, arquivos biométricos externos ao banco e sessões de WhatsApp têm processos próprios.
2. O operador da rotina cifra e autentica o pacote com AES-256-GCM antes de enviá-lo. O recibo registra data, instalação, revisão do banco, tamanho e SHA-256 do arquivo cifrado. A chave fica em configuração protegida, com cópia de recuperação offline sob guarda do proprietário.
3. O coordenador mantém uma cópia local e envia outra para `Meu Drive / Pick-your-Pic Tenants` com a conta Workspace escolhida. Essa pasta é para o banco, separada do arquivo de fotos. Em caso de interrupção, a rotina retoma a mesma cópia do dia depois de verificar o conteúdo parcial.
4. Depois do envio, relê a cópia remota, confere tamanho e SHA-256 e autentica o pacote. O catálogo identifica separadamente quando a cópia foi enviada, conferida e restaurada com sucesso. Falhas ou estados incertos ficam registrados.
5. A retenção planejada mantém sete pontos diários, quatro semanais e três mensais e protege o último ponto recuperável. O ensaio mensal restaura uma cópia em ambiente descartável. As metas a medir são perder no máximo 24 horas de alterações e recuperar o banco em até oito horas.

## Quando precisar de uma cópia ou recuperação manual

- **Antes de uma alteração importante:** solicite uma execução pontual pelo procedimento operacional. Em produção, essa operação deve passar pelos mesmos controles de empacotamento, cifragem, destino, verificação e recibo da rotina. A execução sob demanda depende de um comando operacional validado. O painel ainda não oferece essa ação. O procedimento pontual usado no corte do SaaS comprova uma recuperação anterior, sem comprovar cópia recorrente no Drive.
- **Se precisar recuperar o banco:** escolha o ponto mais recente com recuperação comprovada, obtenha a cópia cifrada e a chave correspondente e confira a integridade, a instalação e a revisão do banco. Restaure primeiro em um PostgreSQL vazio e isolado e valide os dados necessários. A troca de produção em caso de desastre é uma operação posterior, com escopo e aprovação próprios.
- **Se precisar recuperar somente um fotógrafo ou uma pasta:** a restauração individual de dados de um tenant continua pendente. O arquivo de fotos tem destino e fluxo de recuperação separados. A cópia global é útil para investigação em ambiente isolado e inclui os dados dos demais tenants.

[Política aprovada de backup](../../openspec/changes/add-platform-backup-recovery/specs/media-storage/platform-backup-recovery/spec.md) · [Registro do corte SaaS](production-release-2026-11-16.md) · [Checklist pós-deploy](post-deploy-configuration-checklist.md).
