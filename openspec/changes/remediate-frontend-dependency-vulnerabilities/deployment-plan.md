# Plano de publicação da correção do frontend

## Escopo proposto

- Aplicação: Markina Gallery, domínio `markina.pickyourpic.com.br`.
- Projeto Compose documentado: `markina-gallery`, arquivo `docker/docker-compose.yml`.
- Entrada documentada anteriormente: porta pública `8080`; frontend na porta interna `3000`.
- Serviço pretendido: somente `web`/frontend, para incluir o lockfile corrigido; sem banco, migrations, mídia, índice facial, segredos, worker, Redis, proxy ou containers de outros projetos.

## Inventário atual e limite

O acesso SSH somente-leitura a `132.145.193.169` foi tentado em 14/10/2026 com modo não interativo e recusado com `Permission denied (publickey)`. Portanto, o estado atual dos containers, imagem, porta publicada e configuração do servidor não foi confirmado nesta execução. Os valores acima vêm da configuração versionada e do plano operacional anterior, não de uma leitura atual do host.

## Impacto e rollback previstos

Uma futura atualização substitui somente a imagem/instância do frontend pelo build do commit aprovado, preservando as portas e o domínio. A configuração anterior da imagem deverá permanecer disponível para rollback do serviço `web`. Nenhuma operação em banco ou volumes está prevista.

## Gate

Não executar o deploy enquanto o inventário remoto não puder ser confirmado e o fluxo de PR/CI/revisão não estiver concluído. A tentativa SSH não alterou o servidor. Solicitar ao proprietário uma sessão ou credencial de acesso apropriada somente se o inventário seguir necessário após o CI.
