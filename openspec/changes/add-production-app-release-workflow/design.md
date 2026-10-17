# Design

## Context

O release facial em `.github/workflows/ci.yml` valida blobs próprios e publica `web`, `api` e `face-search-worker`. O procedimento `scripts/deploy-prod-web.sh` aceita somente `web`. A estatística exige `api` e `web`, não tem migration e não deve alterar os arquivos do Monitor; reiniciar a API pode causar breve indisponibilidade de todas as rotas que ela serve.

## Goals / Non-Goals

**Goals:**

- Permitir um release estrito de `api` e `web` após CI, inventário somente-leitura e aprovação protegida por fingerprint.
- Manter a autorização e os gates faciais independentes, e fazer a classificação de mudanças falhar fechado em caso de escopo misto.
- Preservar imagens, SHA anterior, revisão do banco e serviços de worker para rollback aprovado.

**Non-Goals:**

- Publicar migrations, alterações de Compose, serviços de worker, processamento facial ou código específico do Monitor.
- Instalar/alterar segredos, arquivos `.env`, proxy compartilhado, DNS, firewall, certificados, redes ou volumes.
- Recriar Nginx ou garantir indisponibilidade zero.

## Decisions

- A política de escopo declarará explicitamente os arquivos de runtime, testes e documentação autorizados para a entrega comercial. O CI comparará os blobs de runtime do SHA candidato com o manifesto versionado; mudanças não declaradas impedem preflight.
- Um classificador da diferença de `main` selecionará exatamente um fluxo: aplicação, manutenção facial ou nenhum. Mudança que pertença aos dois escopos falha sem release automático.
- O workflow terá uma operação manual explícita `app-release` em `main` para repetir ou iniciar o preflight após integração. O padrão manual será inerte; `app-rollback` continuará separado. Ambos executarão os checks completos e manterão inventário somente-leitura e aprovação protegida por fingerprint.
- O inventário de aplicação executará por wrapper SSH de comando restrito e somente-leitura, buscando o script imutável pelo SHA e verificando seu blob Git. Reutiliza a chave dedicada de preflight já configurada; a chave de release permanece restrita ao job `production` após aprovação.
- Para validar que o SHA candidato é o HEAD atual de `main` e descende do checkout ativo, os modos de inventário SHALL usar um repositório bare temporário com filtro de blobs. Essa verificação MUST ser compatível com Git 2.25.1 do host e MUST remover o repositório temporário ao terminar, sem gravar refs, objetos ou `FETCH_HEAD` no checkout ativo.
- O script verificará host, raiz, projeto, origin, checkout limpo, SHA ativo da API, saúde, schema, arquivos Compose ativos, portas e hashes resolvidos de `api`/`web`. O JSON Compose resolvido permanece em memória e não é impresso nem gravado.
- A publicação recriará somente `api` e `web` com `--no-deps`; não executará migration. Depois, verificará hashes e healthchecks, testará o Nginx Markina e os endpoints HTTPS. Se necessário, poderá recarregar somente o processo do Nginx Markina, sem recriá-lo nem alterar sua configuração.
- Fingerprint inclui SHA candidato e estado observado necessário ao rollback. O job protegido recalcula o fingerprint após a aprovação e aborta se qualquer componente divergir.
- O checkout de produção pode avançar após a publicação. A política facial verificará que o baseline autorizado é ancestral do checkout ativo e continuará fixando os blobs faciais permitidos; ela não aceitará alteração facial por causa deste release.
- Uma falha não dispara rollback automático. O procedimento de rollback faz novo inventário, exige aprovação própria e restaura somente as imagens e SHA de `api`/`web`.

## Risks / Trade-offs

- Reiniciar API/web pode interromper brevemente o painel e os endpoints, inclusive a página do Monitor durante a operação → inventário explicita o impacto; o código e os dados do Monitor ficam fora do diff.
- O wrapper root-owned instalado no servidor pode não reconhecer o novo modo de inventário → registrar a atualização do wrapper e seu hash como pré-requisito operacional; não contornar a restrição nem executar release antes do preflight.
- O runtime facial e a aplicação compartilham arquivos de entrada da API/frontend → fixar os blobs candidatos da aplicação, classificar mudanças mistas como bloqueadas e manter o gate facial separado.
- O runtime real pode divergir do inventário anterior → falhar antes de build/recriação e exigir inventário novo.

## Migration Plan

1. Implementar política, testes, scripts, wrapper e jobs de CI sem acessar serviços mutáveis.
2. Passar CI e revisão humana do PR.
3. Atualizar o wrapper root-owned somente pelo procedimento operacional autorizado, conferindo owner, modo e hash do blob.
4. Executar preflight somente-leitura para o SHA exato integrado em `main`; apresentar inventário, portas/subdomínio, impacto, rollback e fingerprint.
5. Aguardar aprovação protegida do Environment `production`; o job repetirá o fingerprint e publicará apenas `api`/`web`.
6. Conferir saúde e smoke tests. Se falharem, preservar estado/imagens e preparar inventário de rollback separado; rollback também exige aprovação humana.

## Open Questions

Nenhuma decisão de comportamento está pendente. A instalação do wrapper e a aprovação do release são gates operacionais humanos, não decisões de arquitetura.
