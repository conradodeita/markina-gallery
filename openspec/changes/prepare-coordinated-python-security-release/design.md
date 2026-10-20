# Design

## Context

Main inicial 27e1b8ffa0917b4dc2120bd4a26e09c6cae47e0f; Oracle limpa nesse SHA após o web-only. Oito IDs distintos, seis conjuntos de camadas: os três workers SFace têm camadas iguais; API/worker têm IDs diferentes. Python observado 3.13.16. Requisitos sem lock não autorizam reinstalar transitivos indiscriminadamente.

## Decisions

1. A entrada oficial permanece deploy-prod-app-services.sh, com --scope python-security separado antes do fluxo legado. O módulo de política carregado do objeto main aprovado oferece plan e simulação explícita. release/rollback/recover reais são recusados antes de qualquer escrita: ainda não existe barreira cooperativa de drenagem nos processos antigos. Não criar um segundo executor operacional nem reutilizar o fluxo legado que recria web.
2. A simulação modela operação sequencial, recibo antes de troca, rollback reverso por ID e preservação de dados/snapshot fora do escopo. É teste de contrato, não homologação de um executor operacional implementado. Não gera approval_code operacional.
3. Candidatos podem ser construídos como camada corretiva sobre cada ID exato inventariado: somente quatro wheels fixados com --no-deps. Python/base, apt, modelos e código permanecem nas camadas anteriores. Conferir pip check e o inventário completo de distribuições: qualquer diferença extra bloqueia. Exportação de imagens Docker, quando viável, é somente leitura, por IDs do projeto e sem volumes; importação/build/testes ocorrem somente no Docker local. Não copiar arquivos de dados ou ambientes do host.
4. O armazenamento local tem cerca de 5,6 GiB livres; importação/build SHALL preservar reserva mínima de 2 GiB. Gemma de aproximadamente 3 GiB pode ser bloqueado por capacidade. Não limpar recursos de outros projetos nem imagens antigas para abrir espaço.
5. O rollout futuro deve proteger entrada API/uploads e claims dos workers com barreira cooperativa e confirmação de fim de ciclo, abrangendo mensagens externas e lifecycle do worker geral. Ausência desse contrato não é resolvida por Redis saudável, fila momentaneamente vazia, SIGSTOP ou timeout seguido de SIGKILL. Essa alteração de runtime não é incluída silenciosamente na autorização restrita a scripts/testes.

## Queue contracts

- Facial/Gemma: jobs duráveis SQL, claim com SKIP LOCKED, token e lease; Redis apenas acorda. complete/fail atualizam SQL. Reclaim consome tentativas; interrupção não equivale a encerramento limpo. Startup index também reconcilia políticas; Gemma recusa ambiente production: não remover esse gate.
- Worker geral: polling SQL com mídia, notificações, providers e lifecycle. Efeito externo pode ocorrer antes do commit; não prometer exactly-once nem interromper arbitrariamente.
- Prévia: processing persistido e recuperação por tempo/fingerprint; loop sem drain cooperativo.
- RAW: processing commitado antes do render, recuperação após 20 minutos e orçamento de tentativas; arquivos temporários/cleanup envolvidos. Não interromper para simular sucesso.

## Validation

Testes determinísticos dos oito cenários solicitados, regressões do executor legado e da classificação sem deploy; builds ARM64 e pip check dos candidatos viáveis; reutilizar CI e testes especializados aprovados apenas se código/pacotes não relacionados permanecem idênticos. Ausência de inferência real/modelo/capacidade ou executor completo permanece bloqueio. Não gerar fingerprint operacional com fixtures.
