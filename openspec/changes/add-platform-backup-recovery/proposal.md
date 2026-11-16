# Proposal: Backups e recuperação da plataforma

## Contexto

O roadmap exige backups diários cifrados do PostgreSQL no Google Drive e testes periódicos de restauração. Ao iniciar esta change, o repositório continha dumps de release/migration, sem coordenador SaaS. O serviço externo dos dois projetos terminou com status 1 em 06/11; o journal apontou reconciliação interrompida. A consulta de metadata posterior encontrou Pick-your-Pic coerente e uma entrada extra preservada no ClearBudget, sem provar causa histórica exclusiva ou recuperabilidade. O diagnóstico equivocado de credencial systemd ausente foi retirado. A política global abaixo foi aprovada antes do novo código local; o coordenador implementado nesta change permanece sem caller de produção ou integração real Drive.

## Goals

- Criar processo de backup independente do arquivamento de fotografias, com políticas, estados, manifestos e restaurações próprias.
- Seguir a cadência diária do PostgreSQL e a retenção aprovada pelo proprietário em 06/11/2026: 7 diários, 4 semanais e 3 mensais; RPO e RTO são metas sujeitas a ensaio, não um SLA declarado.
- Registrar execução, resultado, falhas, proveniência, tamanho e verificação criptográfica/integridade.
- Preparar recuperação global do banco e avaliar restauração lógica de tenant após definir requisitos e comprovar viabilidade sem misturar dados.
- Comprovar restauração em ambiente descartável antes de qualificar um conjunto como recuperável.

## Non-goals

- Usar um dump de release como prova de backup recorrente, teste de restore ou cópia fora do host.
- Arquivar mídias expiradas, remover storage primário ou compartilhar links Drive.
- Restaurar ou migrar produção; qualquer operação remota/destrutiva requer autorização própria.

## Evidência e dependências

- `scripts/deploy-homolog.sh` e scripts de release criam dumps PostgreSQL para operações específicas de implantação/migration. Isso não prova frequência diária, cópia Drive nem recuperação de tenant.
- `docker/docker-compose.yml` não declara serviço de backup; `backend/app/worker.py` executa filas e limpezas, sem job de backup identificado.
- `scripts/README.md` menciona que scripts de backup cifrado PostgreSQL→Drive ainda serão criados; a árvore contém ferramentas de release, por isso esse README não é inventário completo dos scripts atuais.
- Depende de `add-google-drive-storage-foundation`. A conta/plano e fontes independentes permanecem por verificar. O host tem timer diário e um serviço com propósito declarado de backup dos dois projetos; a última execução falhou. Evidência agregada e limites em `inventory.md`; ainda não há prova de artefato nem restore.

## Política aprovada em 06/11/2026

- Backup global diário de todos os tenants; metas iniciais de RPO até 24 horas e RTO até 8 horas, sujeitas a ensaio e sem SLA declarado.
- Retenção de 7 diários, 4 semanais e 3 mensais; ensaio mensal de restore em destino descartável. A retenção de backup não modifica a retenção dos dados ativos.
- Escopo inicial: PostgreSQL completo e configurações essenciais cifradas, incluindo classes pessoais, financeiras e biométricas existentes no banco. Fotos, arquivos biométricos, sessões WhatsApp e recuperação lógica por tenant ficam para etapa própria, por decisão expressa.
- Chave de recuperação sob custódia offline do proprietário, separada do host e da conta Drive. Runtime recebe material protegido; nenhum segredo é criado/configurado pelo executor em ambiente real nesta implementação.
- Cópia no Google Workspace usando identidade dedicada na rotina e conta do proprietário somente no ensaio pré-abertura. Contratos locais usam transporte sintético; quota, destino/permissões, custódia, chamadas reais e publicação/expurgo continuam sob gates próprios.
- A reconciliação de metadata foi concluída: Pick-your-Pic 2/2 sem diferenças; ClearBudget tem uma entrada adicional preservada. O diagnóstico anterior de credencial systemd ausente foi retirado. Detalhes/limites em `inventory.md`.

Aprovação registrada em `policy-decision-draft.md`. O faseamento substitui a proposta inicial de implementar recuperação por tenant nesta primeira etapa.

## Compatibilidade

Manter os dumps de release e seus contratos independentes. Não reutilizar arquivos legados como snapshots novos sem inventário, schema, checksum, origem e teste de restore compatíveis.
