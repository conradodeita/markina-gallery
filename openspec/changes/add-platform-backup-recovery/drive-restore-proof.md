# Recuperação de backup sintético pelo Drive — 17/11/2026

> **EVIDÊNCIA HISTÓRICA — fluxo de runtime próprio aposentado em 25/11/2026.** Este ensaio comprovou o fluxo antigo com PostgreSQL sintético e Drive; não comprova integração do plano atual Restic/Rclone, destino atual ou estado do servidor. A pasta e a configuração citadas não devem ser reutilizadas sem novo inventário e gates vigentes. Nenhum backup real ou timer é autorizado por este registro.

O proprietário autorizou o ensaio completo após a prova de transporte. A origem e o destino eram PostgreSQL 17.11 descartáveis no Docker Desktop local, com rede `none`, dados em tmpfs e nenhuma porta publicada. O Oracle participou somente do transporte do arquivo já cifrado, pela API `bfe511f` e pela conexão do proprietário com escopo `drive.file`. O banco de produção não foi fonte nem destino do backup.

## Evidência da execução

- Execução `cd3516d1-aea6-487c-a199-dd7c58078ad5`, backup `77951336-b603-490c-b2fc-df92a0263997`. O pacote foi gerado por volta de 17h12 BRT, com `pg_dump -Fc`, manifesto e dois itens de configuração sintética. O código existente cifrou com AES-256-GCM e chave aleatória de ensaio em memória.
- O helper de Drive fez upload retomável em uma pasta privada temporária criada pelo app no Meu Drive. Os 6.201 bytes baixados eram idênticos ao original, SHA-256 `31bd57abe0771f9b7099e7fdc25c29ee35683a236869e23f02401fe9d831f998`.
- Antes da restauração, o autenticador GCM recusou uma cópia adulterada enquanto o alvo permanecia vazio. A cópia íntegra baixada foi autenticada e restaurada com `pg_restore --single-transaction` no PostgreSQL descartável. Conferiram os dados das duas linhas de tenants sintéticos, as três linhas financeiras fictícias, os dois campos binários sintéticos, o schema de ensaio `20261105_0106` e o ownership. A origem e o banco sentinela continuaram com seus dados anteriores. A restauração levou 3,344 s neste conjunto pequeno e não mede o RTO de produção.
- Depois do recibo de restauração, a API excluiu somente o arquivo e a pasta temporária. A consulta por ambos os IDs retornou 404. Os dois containers locais do ensaio foram removidos por ID e labels conferidos. Seus dados estavam em tmpfs e a inspeção posterior confirmou a presença dos containers preexistentes. A chave e o conteúdo do pacote não foram persistidos no recibo.
- Na primeira tentativa, upload, restauração e limpeza já haviam sido verificados, mas a confirmação ao Oracle falhou por conflito de nome entre dois imports. A correção foi feita apenas no operador de ensaio. A segunda execução terminou com `verified` e confirmou a ordem de restauração e limpeza.

## Limites

Esta prova cobre uma recuperação completa com dados sintéticos pelo Drive. Depois do ensaio, o proprietário selecionou a mesma conta para a rotina e o app verificou uma [pasta definitiva](../add-google-drive-storage-foundation/production-drive-proof.md#destino-da-rotina-verificado). A custódia da chave operacional, o agendador e a verificação recorrente ainda exigem configuração ou validação. A rotina diária não foi ativada. A recuperação seletiva por tenant e o arquivo de fotos são trabalhos distintos.

[Ensaio de transporte Drive](../add-google-drive-storage-foundation/production-drive-proof.md) · [Checklist pós-deploy](../../../docs/saas-evolution/post-deploy-configuration-checklist.md#3-backup-do-banco-e-configuração-solicitada-por-tenant).
