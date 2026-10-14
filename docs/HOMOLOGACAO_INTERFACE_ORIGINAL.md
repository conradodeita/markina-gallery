# Homologação — interface original de galerias

## Escopo

- Dashboard e navegação administrativa autoral.
- Acervos-fonte, galerias privadas, ajustes, clonagem e exclusão segura.
- Pastas/lotes em preparação, upload JPEG, processamento, liberação e bloqueio posterior.
- Biblioteca, rodadas liberadas, grade protegida, estados de compra, seleção, favoritos, comentários e histórico da cliente.

## Evidências locais

- `ruff check backend/app backend/tests`: aprovado.
- `pytest backend/tests -q`: 32 aprovados; 4 avisos de depreciação do adaptador SQLite do Python 3.12.
- `npm run lint`: sem erros; 6 avisos não bloqueantes relacionados a prévias autenticadas e navegações antigas.
- `npm test`: 11 aprovados.
- `npm run build`: aprovado, incluindo TypeScript e geração das rotas.
- `openspec validate launch-original-gallery-interface --strict`: aprovado.

## Inventário e impacto zero

- Projeto alvo: somente `markina-gallery` em `/opt/markina-gallery`.
- Compose obrigatório: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Domínio alvo: `https://markina-homolog.duckdns.org`.
- Proxy: preservar `npm-network` e alias `markina-homolog-nginx`.
- ClearBudget em `/home/ubuntu/docker/clearbudget`: fora do escopo; nenhum container, volume, rede, imagem ou banco será alterado.
- Não executar prune, `compose down`, remoção de volume ou comando Docker global.

## Dados e roteiro sintéticos

1. Criar cliente sintética, acervo e galeria privada vazia.
2. Criar pasta em preparação e enviar JPEGs sem dados reais de crianças.
3. Confirmar progresso e prévias administrativas.
4. Liberar a pasta para a galeria privada e confirmar bloqueio de novos uploads.
5. Entrar como cliente sintética e validar biblioteca, estados, seleção, favorito, comentário e expiração.
6. Confirmar que outra cliente não acessa a galeria nem seus metadados.

## Rollback

- Registrar commit implantado e imagem anterior antes do deploy.
- Em falha, restaurar somente a imagem anterior do `markina-gallery` e reaplicar o Compose obrigatório sem derrubar o projeto.
- Banco só será restaurado se rollback de código não bastar, usando backup exclusivo do Markina.

## Execução de 2026-08-27

- Aprovação explícita recebida após a apresentação do inventário e do plano de impacto zero.
- Versão anterior: commit `09c9e926e272b624b665edc67a70777a658c5b0c`.
- Versão implantada: commit `461c391b96c52bd823e9b91de1f285676c46a334`, com CI verde no GitHub.
- Backup lógico exclusivo do PostgreSQL criado em `/opt/markina-gallery/backups/predeploy-20260827T040350Z.dump` (`64.522` bytes).
- Manifesto das imagens e da versão anterior criado em `/opt/markina-gallery/backups/predeploy-20260827T040350Z.manifest.txt`.
- O código foi transferido por Git bundle validado porque o `origin` do checkout de homologação permanece apontado para o bundle inicial; nenhuma credencial ou configuração Git remota foi adicionada ao servidor.
- Deploy executado com `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml up -d --build`, sem `down`, prune ou alteração de volume/rede.
- Migration aplicada até `20260827_0005 (head)`.
- Os seis serviços persistentes do Markina ficaram saudáveis; `db` e `redis` não publicam portas e o Nginx permanece restrito a `127.0.0.1:8080`.
- `ClearBudget` permaneceu `running(4)` e o Nginx Proxy Manager permaneceu `running(1)` durante a verificação final.

### Ocorrência operacional resolvida

Após a recriação da API, o Nginx interno do Markina conservou temporariamente o endereço anterior do upstream e `/api/health` respondeu 502. Foi recriado somente `markina-gallery-nginx-1`, com `--force-recreate --no-deps`; o Nginx Proxy Manager não foi alterado. Depois disso, `/healthz` e `/api/health` responderam 200 e todos os healthchecks ficaram verdes.

### Correção após validação visual

- A primeira autenticação visual com a cliente sintética revelou que o grid e o ampliador requisitavam a prévia protegida sem o prefixo `/api`; a API respondia corretamente, mas o frontend consultava uma rota visual do Next.js.
- A tarefa 5.3 foi reaberta imediatamente e a interface passou a normalizar o caminho autenticado, com teste automatizado para o grid e o ampliador.
- Correção publicada e implantada no commit `23b27f7c17690b9668be210fbd6afa260ea807b6`, após CI completo verde.
- Rollback do frontend registrado em `/opt/markina-gallery/backups/pre-preview-fix-20260827T122805Z.manifest.txt`.
- O redeploy reconstruiu somente `web` e recriou somente o Nginx interno do Markina; API, banco, Redis e worker não foram reiniciados.
- A sessão sintética foi recarregada no navegador e confirmou a miniatura e a imagem do ampliador, sem o estado “prévia indisponível”.
- `/healthz` e `/api/health` permaneceram com HTTP 200; os seis serviços do Markina ficaram saudáveis e o ClearBudget permaneceu `running(4)`.

### Evidência sintética

- Acervo: `5162aa4e-886a-4dc6-bdfb-78c2323a7a20`.
- Galeria privada: `42f4a0ff-322a-4d46-9758-1e20b39126ae`.
- Pasta liberada: `3eb27f83-d077-4c57-9eca-5a2a3a066950`.
- JPEG abstrato, sem pessoas: `998ef65a-338e-47f1-9fd0-76d01d4e4de8`.
- Derivados concluídos, prévia da cliente entregue com HTTP 200 e `35.474` bytes.
- Liberação criou um vínculo de foto; tentativa de adicionar outra foto após a liberação foi recusada com HTTP 409.
- Biblioteca da cliente retornou uma galeria e a revisão retornou uma foto selecionada e favoritada, além de comentário sintético persistido.
- Segunda cliente sintética recebeu HTTP 403 ao tentar consultar a galeria da primeira, confirmando o isolamento.

### Estado para revisão humana

A interface final está disponível em `https://markina-homolog.duckdns.org`. A proprietária deve validar os fluxos do fotógrafo e da cliente conforme o roteiro acima antes da sincronização e do arquivamento desta mudança OpenSpec.
