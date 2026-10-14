# Plano de publicação da correção do frontend

## Escopo proposto

- Aplicação: Markina Gallery, domínio `markina.pickyourpic.com.br`.
- Projeto Compose documentado: `markina-gallery`, arquivo `docker/docker-compose.yml`.
- Entrada documentada anteriormente: porta pública `8080`; frontend na porta interna `3000`.
- Serviço pretendido: somente `web`/frontend, para incluir o lockfile corrigido; sem banco, migrations, mídia, índice facial, segredos, worker, Redis, proxy ou containers de outros projetos.

## Inventário atual

Inventário remoto somente-leitura em 14/10/2026, via sessão SSH fornecida pelo proprietário:

- Host: `132.145.193.169` (`clearbudget-vnic`), usuário `ubuntu`.
- Compose `markina-gallery`: 15 serviços em execução e saudáveis; redes e volumes permanecem sob o projeto dedicado.
- Nginx: `127.0.0.1:8080` publicado para `80/tcp` interno.
- Frontend `web`: saudável em `3000/tcp`, sem porta publicada no host e sem volumes montados.
- A etiqueta de configuração Compose do projeto referencia `/opt/markina-gallery/docker/.env.homolog`. O inventário operacional anterior em `../fix-facial-search-latency/deployment-plan.md` confirma que este host serve `https://markina.pickyourpic.com.br` com dados reais. Tratar o ambiente como contendo dados reais independentemente do nome do arquivo.
- O Nginx usa `server_name _` e encaminha tráfego aos serviços `api` e `web`; não foi feita leitura de configuração de segredos.

O nome `.env.homolog` é uma convenção histórica do arquivo, não evidência de que os dados sejam descartáveis. Nenhum container foi reiniciado ou alterado durante o inventário.

## Impacto e rollback previstos

Uma futura atualização substitui somente a imagem/instância do frontend pelo build do commit aprovado, preservando as portas e o domínio. A configuração anterior da imagem deverá permanecer disponível para rollback do serviço `web`. Nenhuma operação em banco ou volumes está prevista.

## Gate

O merge em `develop` aciona `.github/workflows/ci.yml` e `scripts/deploy-homolog.sh`; o script constrói `api`, `web`, `worker` e `migrate`, pode parar os escritores e aplica migrations. Esse fluxo amplo não corresponde ao escopo desta correção. Publicar somente `web` requer uma rota revisada `--no-deps` que consuma o commit aprovado, preserve os overlays ativos e não execute `migrate`, workers, proxy ou demais containers. O CI de PR e a revisão humana precisam terminar antes dessa operação. O inventário desta execução foi somente-leitura.
