# Evidências de validação — 25/10/2026

## Escopo e estado

Autorização direta: corrigir Pillow nos seis especializados antes do Mercado Pago. Worktree `feature/pillow-specialized-security`, PR258 do Dependabot reutilizado, main cef5bdf8 integrada sem reset/force push. Orders permanece no PR283/SHA53959492, CI40194974055 verde (1661 testes backend aprovados/23 skips), sem publicação.

**Nenhum serviço ativo foi substituído, parado ou reiniciado. Nenhuma migration, alteração de credencial, foto real, cobrança ou modificação de dados foi executada.** Nova consulta:15 serviços saudáveis, checkout1f4483bd, schema20261022_0087, HTTPS200 em healthz/api/health/raiz e nenhum marker pendente.

## Origem, licença e compatibilidade

Notas oficiais13.0.0 (16/10/2026): https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html . Python3.13 suportado; licença efetiva MIT-CMU, sem ativação/custo adicional. Avaliadas rupturas fromarray(mode), Image._show, get_child_images, MakerNote e PNG32bits: nenhum consumidor incompatível encontrado em app/spike; fromarray(uint8,RGB) não muda dtype. Nenhuma licença/revisão de modelo mudou.

Wheel oficial PyPI13.0.0 CPython313 ARM64 manylinux_2_27/2_28:6.515.908bytes, SHA256 `19b66ca0a4d25cc0200b381ce824c7ea090db61427315e73cfb05dbf1b35c369`. Manifesto: https://pypi.org/pypi/Pillow/13.0.0/json . Download HTTPS files.pythonhosted.org, tamanho/checksum conferidos, instalação offline sem resolver dependências.

O primeiro ensaio bloqueou diferenças de resize de retratos. Fonte oficial Resample.c13 confirmou mudança da ordem dos passes; os dois oráculos explícitos continuam bit a bit iguais entre versões e cada resize automático deve corresponder exatamente à regra respectiva. Sem tolerância geral. Na amostra RGB: máximo15/255, RMSE0,628; CMYK12/255, RMSE1,187; L2/255, RMSE0,477. Outros contratos iguais. Ver design; não alegar equivalência absoluta de qualquer fotografia.

## Seis candidatos nativos

Recibos0600 em pasta0700 no host: `pillow-prepare-20261025-01/prepared-v2.json`, provas individuais/logs e `signal-import-rehearsal.json`. IDs completos nos recibos; prefixos abaixo:

| Serviço | Anterior | Candidato | Pacotes comparados |
|---|---|---|---|
| face-index-worker |3f127a03e2c7|1b34cf3b2195|62|
| face-search-worker |5c783d14d971|ae32bc36c0d6|62|
| face-maintenance-worker |0bdc5fec1035|dd9a526e220a|62|
| face-gemma-index-worker |d353c1a5afc8|adca63778e0d|90|
| preview-adjustment-worker |4d17f0b3f06a|c7ded32123ee|60|
| raw-development-worker |8bb5cff14306|ec62cb836dad|60|

Pillow13.0.0 nos seis candidatos; Python3.13.16 e demais pacotes idênticos; pip check0 antes/depois. Fontes/manifests/migrations/modelos por hash, camadas anteriores preservadas e somente label adicional de rastreio. BuildKit precisou de alias local por conteúdo porque FROM com ID nu tenta resolução remota; nenhuma tag ativa sobrescrita. Sem apt, pull de base, Dockerfile normal, download de modelo ou inferência biométrica.

Matriz offline anterior/candidato: JPEG RGB/L/CMYK×EXIF1/3/6/8, orientação, dimensões, normalização RAW real sem EXIF, watermark/apresentação reais, referência BGR real onde NumPy está instalado, PNG RGBA/P/I;16 e thumbnails480/1600/2000 de padrão7MP. Limites1CPU/1GiB, sem rede, mounts, filas ou chaves de produção. Tempos/RSS nos recibos; ensaio curto não é benchmark de carga/calibração facial.

Imports dos seis entrypoints passaram. Containers descartáveis com imagens candidatas: wchan ocioso, suspensão de unless-stopped, SIGINT→130, retomada, restauração da política e limpeza SIGTERM→0; nenhum SIGKILL. Somente containers identificados do ensaio foram removidos. Consumidores reais mantiveram IDs/imagens/StartedAt. Lock ensaiado em pasta temporária: concorrência recusada e liberação posterior confirmada.

## Testes e limites

-2 testes de pin/consumidores,13 de candidato/origem/deriva/algoritmo/recibos e12 de orquestração sintética passaram. Cobrem aprovação/CI/inventário/filas, parada/saúde/digest, recuperação antes do snapshot e composição parcial, configuração/mounts preservados.
-9 testes de contrato técnico de candidato passaram; dependência continua recusada para publicação API/web. Reexecutar o teste completo de workflow após commit dos manifests: o HEAD anterior continha só spike/documentação e era categoria none, não a alteração backend ainda sem commit. Nenhum executor antigo foi ampliado.
-Ruff dos novos scripts e OpenSpec strict passaram. Sem limpeza de runtime elegível; apenas asserção da categoria de recusa técnica corrigida com regressão.
-Backend local:77 cenários passaram inicialmente com Pillow13.6 falhas de harness: chave sintética de startup ausente e SQLite em memória não compartilhado pelo TestClient;4 passaram após chave explícita. Reexecução completa com DB sintético em arquivo em andamento.19 testes faciais/provider Gemma passaram em venv existente com NumPy/Pillow12.3 (regressão de fonte, não prova de13); versão13 facial coberta nas imagens ARM64 e sujeita ao CI com face-requirements.

## Gates pendentes

Diff final/CI de PR e main/revisão humana do PR258. Ainda não há recibo selado/fingerprint operacional aprovado nem published.json. Runbook descreve aplicação/recuperação sem DDL. Depois da correção efetiva, renovar inventário/overlay/fingerprint Orders; não reutilizar o recibo antigo nem declarar Mercado Pago publicado. Nenhuma spec principal sincronizada/change arquivada sem revisão humana.
