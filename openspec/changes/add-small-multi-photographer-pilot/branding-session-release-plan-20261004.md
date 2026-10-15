# Pacote sucessor — branding por fotógrafo e recuperação de sessão

## Escopo e autorização

Aceite humano04/10: corrigir falha da publicação da PR136 e incluir tratamento de timeout; autorização adicional explícita para PR sucessora com somente essas correções/testes/registros, após validação local. PR136 já está MERGED2d688e4. Não reabrir/reintegrar a PR antiga. Utilizar a branch existente, sem descartar mudanças, nova branch, force push ou inclusão de onboarding/canal/Device preexistentes. Base develop contém o merge aprovado. Merge/deploy da sucessora ainda exigem verde humano e pacote/inventário fresco; envio dos150JPEGs continua separado.

## Falha e solução

O deploy falhou no helper de branding por assumir registro global único. A instalação tem três fotógrafos, mas leitura SQL real readonly16:29Br confirmou dois registros de branding de owners distintos com três referências legacy e nenhuma scoped; o novo contrato aceita essas referências. Três owners/paths scoped foram validados em fixture para a próxima configuração de C. Preservar registros únicos por owner e keys geradas pela API, incluindo legacy; manter hashes/backup/limites/sem overwrite/guardas e recusar ambiguidade real. Inventário e ancestrais antes da parada, conferência após parar, restart em falha. Nenhuma migration ou pool/quota modificados.

SessionBoundary cobre rotas protegidas de ambos os papéis, sem interceptar entrada e confirmação/recuperação pública. Verificação contextual antes da montagem, em navegação/foco e60s; limite10s. API de destino distingue401 de403 sem alterar recusas das outras rotas. Sessão inválida desmonta privado/limpa cache facial e redireciona à entrada; fotógrafo refaz senha/TOTP, cliente sem capacidade válida reabre link original para OTP. Rede/408/5xx têm aviso/retry de leitura, sem logout ou replay de upload/compra/OTP. Contexto/retorno não concedem owner/acesso, tokens/queries/PII não são armazenados no retorno.

## Inventário e impacto previsto

Leitura15:48Br confirmou9b72f2b/schema0071/13healthy; domínio exclusivamente homologação `markina-homolog.duckdns.org`, checkout `/opt/markina-gallery`, Compose projeto `markina-gallery` e arquivo `docker/docker-compose.yml` com overlays próprios existentes. Única porta publicada própria127.0.0.1:8080→80; API/web/DB/Redis/Evolution permanecem internos. Ambiente e19tabelas preservados;8containers de terceiros idênticos. CPU/RAM/disco/clientes/filas devem ser reinventariados imediatamente antes do novo aceite de publicação, não reutilizar este timestamp como preflight futuro.

Workflow existente após merge autorizado reconstrói aplicações, cria backup restrito, preserva branding no volume próprio existente, para escritores próprios e executa cadeia Alembic sem nova revisão, recriando aplicações próprias. Pode haver indisponibilidade temporária; não prometer zero downtime do produto. Impacto zero significa nenhuma mudança de terceiros, portas/DNS/proxy/firewall/certificados, segredos/env ou nova infraestrutura. Não fazer hotpatch/deploy manual/prune/down/restauração por inferência. Backup lógico pré136 é apenas legível/verificado por TOC/hash, não prova de restauração.

## Gates

Pacote local conferido:21branding(19passes/2skips explícitos), políticas shell,71regressões backend e snapshot seletiva33backend/424frontend/54arquivos, lint0erros/typecheck/build padrão, OpenSpec76/0 e Gitleaks semleaks. Runtime isolado físico resolveu falha de junction externa do Turbopack, sem mudar produto/dependências. Validações/resultados específicos em `validation.md`; CI/revisão/deploy não foram substituídos por esses checks.

1. Snapshot do índice sem alterações locais não relacionadas: branding/políticas, regressões backend auth/prévias, frontend completo/lint/typecheck/build, OpenSpec estrito, diff e gitleaks.
2. PR sucessora criada/anexada; proprietário acompanha CI, executor não usa watch/poll de verde.
3. Após verde humano, conferir SHA/candidato, inventário/backup novo e autorização explícita de merge/publicação; pacote aqui não é autorização automática.
4. Após execução existente, verificar HEAD/last-healthy/schema/13healthy/health200, fingerprints/ambiente/terceiros e prévias/monitor/entrada autenticada, sem expirar sessão real por conta própria.
5. Somente depois, scopes privados/fontes50/conta/zero upload em andamento, novo collector real ativo e confirmação humana antes de liberar150uploads. Alertas antigos permanecem registrados.

## Rollback e limites

Manter rollback de código e reinício conservador do workflow; nenhuma operação destrutiva de dados. Falha de preservação reinicia API anterior; diferença de hash ou ownership aborta, não sobrescreve/ignora owners. CI PostgreSQL e testes real-container/symlink Linux complementam as provas locais explicitamente limitadas. Sem autorização de cleanup das galerias/clientes/referências ou de produção.
