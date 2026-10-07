# Resultado do inventário de homologação

- Execução: [Actions run 37532440468](https://github.com/conradodeita/markina-gallery/actions/runs/37532440468), concluída com sucesso em 2026-10-06 (UTC).
- SHA esperado e implantado: `ea259a64e4e83f5f7bbb4bed76647f92ce325508`.
- Escopo: projeto Compose `markina-gallery`, checkout `/opt/markina-gallery`, arquivo `docker/docker-compose.yml`; a verificação concluiu que os volumes são nomeados e próprios do projeto. Foi usado um único container transitório de consulta (`--rm --no-deps`). Nenhum deploy, migration, backup, limpeza, reinício ou alteração ocorreu.
- Entrada de rede: domínio `markina-homolog.duckdns.org`; única publicação Compose em `127.0.0.1:8080 -> 80` via nginx. PostgreSQL e Redis não publicam portas.
- Saúde: 13 serviços/entradas ativos reportados como `Up`/saudáveis; `/healthz` e `/api/health` responderam HTTP 200.
- Banco: revisão Alembic `20261001_0071`; 3 fotógrafos, 6 clientes e 5 galerias.
- Mídia: 814 fotos e 2.442 registros `media_derivative`; 3.244 arquivos de derivados, total de 647.019.097 bytes. Volumes de originais temporários, histórico e referências faciais sem arquivos, compatível com a retenção do código implantado, que remove a fonte temporária após processamento.
- Filas duráveis: mídia 814 total, facial 849 total e ajuste de preview 802 total; em todas, 0 queued, 0 processing e 0 failed.
- Capacidade do disco do volume consultado: 203.034.800 KiB total, 88.257.236 KiB usados e 114.761.180 KiB disponíveis (44% usados).
- Observações: o inventário encontrou um container de migração antigo em estado `Exited (255)`, criado há cinco semanas; a revisão atual do banco e as verificações de saúde estavam corretas. O serviço `preview-adjustment-worker` estava ativo apesar de aparecer como órfão na configuração Compose base; o script de deploy vigente detecta e preserva esse worker usando o overlay correspondente.
- Limite do fluxo de limpeza: `homolog_cleanup.inventory` informou `unavailable_multiple_photographers`; nenhuma limpeza foi executada.
