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
- O inventário de aplicação executará por wrapper SSH de comando restrito e somente-leitura, buscando o script imutável pelo SHA e verificando seu blob Git. Reutiliza a chave dedicada de preflight já configurada; a chave de release permanece restrita ao job `production` após aprovação.
- O mesmo wrapper read-only terá um comando separado que exporta por stdout somente a imagem do container API ativo, conferida pelo ID obtido no inventário e pelo SHA `main` exato. Não lê volume, ambiente, filesystem do container ou dados; não grava no host. O bundle de base é privado no Actions por um dia e permite construir em CI uma camada que preserva todas as dependências de produção.
- O script verificará host, raiz, projeto, origin, checkout limpo, SHA ativo da API, saúde, schema, arquivos Compose ativos, portas e hashes resolvidos de `api`/`web`. O JSON Compose resolvido permanece em memória e não é impresso nem gravado.
- A CI constrói a API sobre o ID da imagem exportada e inventariada, copiando apenas `backend/app`, como faz o bridge root-only; a imagem web usa seu Dockerfile aprovado. O bundle API/web ARM64 do SHA exato é recebido por chave SSH separada com forced command restrito somente após aprovação `production`. O script revalida SHA-256, manifesto, IDs, ID-base, arquitetura e origem após preservar as imagens de rollback; não executa `compose build` no host. Recria somente `api` e `web` com `--no-deps`; não executa migration. Depois, verifica hashes e healthchecks, testa o Nginx Markina e os endpoints HTTPS. Se necessário, pode recarregar somente o processo do Nginx Markina, sem recriá-lo nem alterar sua configuração.
- Fingerprint inclui SHA candidato e estado observado necessário ao rollback. O job protegido recalcula o fingerprint após a aprovação e aborta se qualquer componente divergir.
- O job de preflight calcula um digest não sensível de host/porta/usuário usados na conexão SSH. Antes do upload, o job `production` recalcula o digest com suas próprias variáveis e compara o resultado; qualquer divergência encerra o release antes de transferir o bundle ou conectar para deploy.
- O checkout de produção pode avançar após a publicação. A política facial verificará que o baseline autorizado é ancestral do checkout ativo e continuará fixando os blobs faciais permitidos; ela não aceitará alteração facial por causa deste release.
- Uma falha não dispara rollback automático. O procedimento de rollback faz novo inventário, exige aprovação própria e restaura somente as imagens e SHA de `api`/`web`.
- Para publicar o código do backup global, o manifesto fixa os blobs exatos dos módulos da API/UI e os arquivos de suporte da rotina. A exceção de classificação limita-se ao módulo `backend/app/platform_backup/runtime_worker.py`; isso não autoriza criar ou iniciar um processo de worker. O deploy API/web não instala unidades, timer, chave/configuração do backup, nem faz cópia real. O schema e a imagem ativa precisam corresponder ao inventário ao vivo antes de atualizar os pins.

## Risks / Trade-offs

- Reiniciar API/web pode interromper brevemente o painel e os endpoints, inclusive a página do Monitor durante a operação → inventário explicita o impacto; o código e os dados do Monitor ficam fora do diff.
- O wrapper root-owned de inventário não pode receber arquivos e a chave de deploy atual não usa forced command → acrescentar somente export read-only da imagem API ao wrapper atual, mantendo-o sem escrita, e criar wrapper root-owned separado para upload limitado e uma chave privada/pública exclusiva; exigir secret no environment `production` e instalação autorizada antes do release; não contornar a restrição.
- O runtime facial e a aplicação compartilham arquivos de entrada da API/frontend → fixar os blobs candidatos da aplicação, classificar mudanças mistas como bloqueadas e manter o gate facial separado.
- O runtime real pode divergir do inventário anterior → falhar antes de build/recriação e exigir inventário novo.

## Migration Plan

1. Implementar política, testes, scripts, wrappers e jobs de CI sem acessar serviços mutáveis. O artefato é criado apenas em push de `main` com escopo `app`, após sucesso dos gates completos, e fica restrito ao run/SHA.
2. Passar CI e revisão humana do PR.
3. Atualizar o wrapper read-only de inventário e instalar separadamente o wrapper de upload root-owned, conferindo owner, modo, hash e forced command; cadastrar a chave privada do recebedor restrito somente como secret do environment `production`. O deploy usa essa chave apenas para transferir o bundle após aprovação.
4. Executar preflight somente-leitura para o SHA exato integrado em `main`; apresentar inventário, portas/subdomínio, impacto, rollback e fingerprint.
5. Aguardar aprovação protegida do Environment `production`; o job repetirá o fingerprint e publicará apenas `api`/`web`.
6. Conferir saúde e smoke tests. Se falharem, preservar estado/imagens e preparar inventário de rollback separado; rollback também exige aprovação humana.

## Open Questions

Nenhuma decisão de comportamento está pendente. A instalação do wrapper e a aprovação do release são gates operacionais humanos, não decisões de arquitetura.
