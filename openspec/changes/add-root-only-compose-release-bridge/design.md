# Design

## Context

O preflight `44283691264` falhou antes de qualquer deploy. O proprietário escolheu a ponte root-only. A leitura read-only de 18/11/2026 confirmou fontes e diretórios diferentes de API/web e ausência do label `config-hash` em ambos. O proprietário autorizou explicitamente prova semântica por serviço. O recibo web compartilhado é anterior à imagem ativa e não comprova a identidade atual.

## Goals / Non-Goals

**Goals:** comprovar a configuração efetiva por serviço; preservar imagens, dependências faciais e rollback; manter CI, escopo, lock, aprovação e saída sem segredos.

**Non-Goals:** migrar para Compose canônico; alterar ambiente, schema, dados, workers ou recursos compartilhados; recriar containers para adicionar labels; expor configuração ou shell root.

## Decisions

- Helper de biblioteca padrão em `/usr/local/sbin/markina-gallery-app-compose-bridge`, `root:root 0755`. Dispatch explícito em `main`, Environment `production`, confere host, repositório, SHA/blob, backup, checksum e invariância dos containers. O forced-command wrapper continua pinado ao script app e só oferece inventários. Não modificar sudoers, chaves ou permissões existentes.
- O instalador aceita somente as origens canônicas exatas `https://github.com/conradodeita/markina-gallery.git`, `ssh://github.com/conradodeita/markina-gallery.git` e `git@github.com:conradodeita/markina-gallery.git`. A última é a forma SCP do OpenSSH observada no checkout real; aceita somente o usuário fixo `git`, host e caminho exatos. Não reescrever `remote.origin`; rejeitar host, caminho, protocolo, usuário ou credenciais diferentes antes de qualquer escrita privilegiada.
- Git, escopo e lock comum permanecem sob `ubuntu`. A ponte exige UID/GID root e tabela fechada de argumentos antes de qualquer consulta. Mutação exige modo apropriado, SHA/marcador correspondentes, lock ocupado e cópia root-only ligada ao fingerprint aprovado.
- Selecionar exatamente uma API e um web por labels. Arquivos e diretório são próprios de cada serviço. No `deploy-state`, aceitar snapshots e diretórios sem symlink pertencentes a `root` ou ao proprietário do checkout somente quando a árvore e os arquivos não concederem acesso a grupo/outros; os arquivos também devem ser legíveis pelo proprietário, não executáveis e sem hard links. Recusar outros proprietários/modos e hash divergente. Fontes versionadas devem corresponder ao blob de `HEAD`.
- Exceção aprovada para planejamento em 19/11: uma base privada de adoção pode substituir as fontes dos labels somente após operação protegida explícita. Os labels antigos permanecem como proveniência histórica, sem alegação de equivalência. Não sobrescrever fontes antigas nem adotar automaticamente ao encontrar divergência.
- Resolver com cópias temporárias privadas das fontes e ambiente, mantendo `--project-directory` original e perfis fixos facial/preview. Remover cópias temporárias ao sair. Inventário não grava estado persistente nem altera imagens/containers. Nunca devolver stderr bruto, ambiente ou JSON Compose.
- Comparar snapshot resolvido com Docker inspect e defaults da imagem: ambiente sem duplicatas, comando/entrypoint, usuário/diretório, healthcheck, labels da aplicação, mounts, redes, restart, limites, privilégios, capabilities, segurança e portas. Campo sem contrato conhecido falha fechado. Digest semântico é distinto do label Compose; não sintetizar labels ausentes.
- Identidade web inicial exige prova do snapshot e revisão `io.pickyourpic.release` igual ao checkout ancestral aprovado. Não reescrever recibo antigo durante inventário. Após release, o novo recibo vincula imagem/digest semântico; recibos legados de hash Compose não substituem essa prova.
- Antes de build, preservar fontes byte a byte, modelos, metadados e fingerprint em `/var/lib/markina-gallery/app-compose-bridge/<operação>/` (`root:root 0700`, arquivos `0600`), fora do estado compartilhado gravável por ubuntu. Fontes originais permanecem intactas; nenhuma retenção/limpeza automática.
- API é construída sobre o ID imutável da imagem ativa, copiando somente `backend/app` obtido por `git archive` do SHA aprovado. Recusar qualquer mudança em requisitos, Dockerfile ou migrations. Isso conserva dependências/modelos faciais instalados. Web usa o contexto/Dockerfile versionados. Nunca usar contexto de build arbitrário extraído de snapshot.
- Publicação clona o modelo comprovado, fixa defaults da imagem antiga e altera somente imagem e `APP_VERSION` da API. Provar configuração prospectiva antes de trocar containers. Redes/volumes são externos; remover build/dependências do modelo aplicado. Executar por serviço com `--no-deps --no-build --pull never`.
- Rollback exige inventário/aprovação próprios, cópias e imagens verificadas do último release e preservação do runtime substituído. Restaurar somente API/web, sem banco ou segredos. Falha não dispara rollback automático. Nginx recebe apenas teste de configuração e reload já previstos.
- Confirmar imagens/versão, semântica, schema `20261113_0126`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, saúde e HTTPS antes de registrar sucesso. Falha conserva marcadores e recuperação.

## Risks / Trade-offs

Snapshots, defaults ou formatos sem contrato suportado bloqueiam; suporte adicional exige fixture e comparação efetiva. Fontes em `deploy-state` aceitam somente a árvore privada do root ou do proprietário do checkout; recuperação persistente continua root-only. A fronteira root exige validação de argumentos, caminhos, modos, hash e negativas. API/web têm interrupção breve; builds/provas terminam antes e recuperação fica preservada. O estado privado cresce até existir política de retenção aprovada.

## Migration Plan

### Reconciliação do runtime ativo aprovada em 19/11/2026

1. Diagnóstico separado do preflight aprovável: inventariar API/web, imagens por ID, revisão, saúde, fontes históricas e categorias de divergência. Manter valores de ambiente, modelos completos e caminhos sensíveis no processo root. A saída minimizada distingue prova de tradução do runtime de equivalência com fonte histórica; uma não substitui a outra.
2. Preparar um modelo por serviço a partir do runtime ativo e defaults das imagens fixadas. Usar rede/volume existentes como externos e preservar bind mounts, ambiente completo (inclusive TOTP), comandos, usuário, healthcheck, labels de aplicação, limites e políticas. Representar somente campos com contrato explícito; campo desconhecido bloqueia. Acrescentar cobertura de `tmpfs` e namespace de cgroup com opções preservadas, comparação normalizada e negativas; não aceitar todo `HostConfig` por cópia opaca.
3. Resolver o modelo candidato com Compose em diretório temporário root-only, sem `up`, `build`, `load`, tags ou escrita persistente. Comparar o resultado e defaults das imagens com inspeção Docker independente, sem reutilizar a função geradora como oráculo. Confirmar invariância dos containers, imagens e fontes antes/depois. Nenhum teste pode ocultar a divergência do snapshot histórico para produzir um fingerprint de release.
4. Produzir fingerprint exclusivo de adoção, com domínio distinto do fingerprint de release, vinculado a SHA de suporte, IDs completos de containers/imagens, identidade semântica de ambos, hashes das fontes históricas e do modelo candidato, versão e resultado dos gates de saúde/schema/ambiente facial. A aprovação é inválida se qualquer entrada mudar. `.env` permanece intacto; nenhum valor TOTP é criado, removido ou rotacionado.
5. Após CI/revisão e autorização operacional separada, workflow protegido `production` e lock comum repetem toda a prova e persistem uma base imutável sob raiz fixa privada da ponte (`root:root 0700`, arquivos `0600`). O manifesto registra proveniência, identidade, hashes e fingerprint aprovado; fontes antigas são copiadas byte a byte para recuperação sem alteração das originais. O material contém segredos e não sai do host nem entra em logs, artifacts ou Git. Falhas não ativam uma base incompleta.
6. Selecionar base somente por registro root-owned em localização fixa, nunca por caminho fornecido por SSH. Publicar o registro atomicamente após prova, preservando registro anterior. No inventário, base ausente mantém o fluxo original por labels; base selecionada inválida/adulterada/obsoleta falha fechada, sem fallback silencioso. Validar metadados, hashes, IDs e semântica atuais em cada uso. Não fabricar `config-hash` ou alterar labels de containers.
7. A adoção não publica a aplicação: após persistência e confirmação de invariância, executar novo preflight de release. Release e rollback continuam com aprovações/fingerprints próprios. O ciclo completo deve vincular as fontes e IDs novos ao registro após release saudável, preservar os IDs/fontes anteriores para rollback e manter recuperação explícita em falha parcial; não deixar uma base presa ao container substituído nem aprovar um runtime parcialmente trocado.
8. Instalação da ponte revisada, adoção persistente e deploy são operações distintas. A aprovação desta revisão documental não executa nenhuma delas. A chave/secret de upload de artifact continua dependência operacional separada da change `add-production-app-release-workflow`.

1. Fechar fixtures/prova, helper, integração, instalador, workflow e runbook; executar gates locais proporcionais ao risco.
2. Revisar diff/segredos, commit, push, CI/PR e merge verde.
3. Dispatch protegido instala ponte/wrapper e confere hash/metadados e invariância. Fetch somente dos objetos de main sem trocar checkout.
4. Preflight read-only confirma semântica, schema, facial, portas/domínio e fingerprint; divergência impede mutação.
5. Aprovação protegida e fingerprint idêntico permitem API/web; validar runtime, saúde/HTTPS e recuperação antes de marcar conclusão.

## Open Questions

Nenhuma decisão arquitetural pendente após a autorização da prova semântica. A exceção de owner no `deploy-state` é limitada à árvore privada e ao proprietário do checkout; qualquer outro owner/modo continua bloqueado. Gates operacionais ainda podem bloquear campos não comprovados.

A direção da adoção explícita foi aprovada em 19/11. Os contratos acima ainda precisam de implementação e testes; não constituem evidência de uma base adotada. A autorização operacional para persistir cópias privadas de configuração e ativar o registro ainda deverá ser vinculada ao diagnóstico/fingerprint exatos.
