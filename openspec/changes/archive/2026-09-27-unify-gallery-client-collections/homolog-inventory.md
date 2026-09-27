# Inventário somente leitura de homologação — 2026-09-27

## Leitura atual e diferença

- O [workflow 36350841071](https://github.com/conradodeita/markina-gallery/actions/runs/36350841071) passou nos jobs backend, frontend, OpenSpec, gitleaks e deploy/inventário. O checkout publicado e inventariado é `58f5dd8723184e5a1a0f115507c22a51920aeaf1`; `/healthz` e `/api/health` responderam com saúde.
- A topologia resolvida confirmou projeto `markina-gallery`, entrada exclusiva `127.0.0.1:8080`, domínio `https://markina-homolog.duckdns.org`, banco/Redis sem portas públicas e volumes de mídia da Markina. Evolution permaneceu saudável e separado do alvo da manutenção.
- Contagens atuais: 7 galerias públicas, 1 derivada legada, 7 pastas, 1.700 fotos, 1 cliente, 2 registros, 1 membro privado, 0 seleções e 7 pedidos. Há ainda 35 sessões de cliente, 105 desafios OTP, 13 inscrições push, 27 eventos de notificação, 36 entregas WhatsApp e históricos técnicos vinculados. O inventário completo discrimina as 57 tabelas operacionais; algumas contagens foram mascaradas pelo filtro de segredos do GitHub no log, sem impedir o teste de pós-condição zero.
- Mídia atual: origem 7 arquivos / 5.452.814 bytes; derivados 6.786 arquivos / 1.481.611.860 bytes; histórico e referências faciais 0. Em 26/09 eram 19 arquivos de origem / 94.950.818 bytes; as contagens centrais de galerias, fotos, clientes e pedidos não mudaram. Desafios OTP aumentaram de 34 para 105.
- Preservação inventariada: 1 admin, 66 sessões administrativas, 3 desafios de segurança, 15 inscrições push administrativas, 1 marca, 1 PIX global, 7 configurações de notificações, 2 presets de preços com 5 faixas, 1 configuração de WhatsApp, 1 configuração de ajuste de prévia, além das demais tabelas administrativas/globais classificadas em `backend/app/homolog_cleanup.py`.

## Gate para limpeza autorizada sem novo backup

- Excluir somente as 57 tabelas operacionais da Markina, as linhas de cliente nas 3 tabelas mistas, o conteúdo das quatro raízes `source`, `derivatives`, `history` e `facial-references`, e as filas do Redis exclusivo da Markina. Pausar e retomar somente writers do projeto; não tocar em Evolution, branding, banco/volumes/contêineres de terceiros, admin, 2FA, configurações globais, backups preexistentes ou produção.
- O fluxo sem novo backup não repete o deploy. Antes de enviar o script de manutenção, o workflow exige o SHA acima como ancestral, confirma que nenhum código operacional mudou, confere que o checkout remoto ainda está nesse SHA e verifica as duas rotas de saúde. O script repete as guardas de topologia e o inventário antes de excluir; após, compara preservados e exige tabelas/mídia operacionais zeradas.
- O proprietário autorizou a limpeza dos dados de teste sem criar novo backup e recebeu o escopo, porta, subdomínio e plano de impacto zero no chat antes da execução registrada abaixo.

## Primeira limpeza — 2026-09-27

- O [workflow 36353174348](https://github.com/conradodeita/markina-gallery/actions/runs/36353174348) passou nos cinco jobs. O commit `843b4584d3c2e831d488e03148e0f36ee037ef3b` continha os trailers literais de limpeza sem backup e SHA esperado `58f5dd8723184e5a1a0f115507c22a51920aeaf1`. O job conferiu o checkout remoto e os healthchecks e executou a manutenção sem novo deploy nem backup de pré-deploy; o script confirmou o token exclusivo de limpeza sem novo backup.
- Inventário imediatamente anterior: 7 galerias, 1 derivada legada, 7 pastas, 1.700 fotos, 1 cliente, 7 pedidos, 35 sessões de cliente, 105 desafios OTP, 190.611 eventos de auditoria de cliente, 6.786 derivados / 1.481.611.860 bytes e 7 fontes / 5.452.814 bytes. O número de eventos de auditoria e alguns outros contadores aumentaram entre a leitura e a pausa dos writers; o gate repetiu a leitura no momento da operação.
- Inventário posterior: **zero em todas as 57 tabelas operacionais**, zero arquivos/bytes nas quatro raízes de mídia e zero linhas de cliente nas três tabelas mistas. A comparação automática confirmou contagens preservadas idênticas antes/depois: 1 admin, 66 sessões administrativas, 3 desafios de segurança, 15 inscrições push administrativas, 1 marca, 1 PIX global, 7 configurações de notificações, 2 presets com 5 faixas, 1 configuração WhatsApp e 1 configuração de ajuste de prévia, entre outras. O Evolution estava saudável no inventário, sem comandos de exclusão/recriação dirigidos a ele; o healthcheck HTTP da Markina passou após retomar os serviços.
- Nenhum dado sintético de aceite foi criado. O proprietário informou em 27/09 que verificou pela interface, fora da aba do executor, que o sistema está vazio, e decidiu encerrar a change com essa verificação. A validação funcional remota com dados novos e a segunda limpeza foram dispensadas, sem alegar que foram executadas; os contratos de audiência/compra têm evidência de testes isolados e CI.

## Leitura anterior — 2026-09-26

## Alvo e topologia

- Servidor Oracle compartilhado; checkout exclusivo `/opt/markina-gallery` no SHA `f4968f32410ffdfc30979440dfe0bb9dc16639c8` no momento da leitura.
- Projeto Compose `markina-gallery`; entrada do projeto `127.0.0.1:8080`, subdomínio `https://markina-homolog.duckdns.org`. PostgreSQL e Redis da Markina sem portas públicas. Nginx Proxy Manager, Firefly/companheiros e Portainer são recursos alheios e ficam fora do escopo.
- `nginx`, `web`, `api`, `worker`, workers faciais, worker de ajuste de prévia, PostgreSQL/Redis da Markina e serviços Evolution estavam saudáveis. A instância/login e o banco/Redis da Evolution SHALL permanecer intactos.
- A API corrente usa `APP_ENV=staging`; a rotina existente de inventário/limpeza usa contêiner efêmero com `APP_ENV=homolog`. Para esta leitura somente, o comando `docker exec -e APP_ENV=homolog ... --mode inventory` confirmou as contagens, sem mutação. Antes de executar a limpeza, o procedimento SHALL confirmar adicionalmente checkout, domínio, Compose, banco e volumes exclusivos; a variável sobrescrita sozinha não é prova de ambiente.

## Contagens agregadas atuais

| Categoria | Contagem |
| --- | ---: |
| Galerias públicas | 7 |
| Galerias derivadas | 1 |
| Pastas | 7 |
| Fotos registradas | 1.700 |
| Clientes | 1 |
| Registros públicos / membros privados | 2 / 1 |
| Seleções / pedidos / comunicações de pagamento | 0 / 7 / 6 |
| Sessões / desafios OTP de cliente | 35 / 34 |
| Entregas WhatsApp / operações de lifecycle | 36 / 8 |
| Arquivos de origem | 19; 94.950.818 bytes |
| Derivados | 6.786; 1.481.611.860 bytes |
| Histórico de mídia | 0 |

## Preservação observada

- 1 conta admin, 66 sessões administrativas e 3 desafios de segurança administrativos; o segredo TOTP pertence a `admin_user`.
- 1 configuração de marca, 1 PIX global, 0 modelos de pagamento, 2 presets de preço e 1 configuração de canal WhatsApp.
- O inventário atual **não cobre todas** as configurações globais, inscrições push, notificações, auditorias e recibos técnicos. A execução depende de estender o inventário e provar a classificação de cada tabela e raiz afetada, inclusive ausência de históricos de clientes depois da limpeza.

## Escopo autorizado e gate

- O proprietário confirmou que os dados de homologação acima são de teste e pediu apagar também seleções, compras, pedidos e históricos de clientes, preservando admin, 2FA, Evolution e **todas** as configurações globais. Para esta limpeza, dispensou **novo** backup; backups preexistentes não serão removidos.
- Esta leitura não executou limpeza. Antes de qualquer ação destrutiva, repetir o inventário no SHA que será usado, apresentar diferenças, lista de tabelas/arquivos/filas atingidos, porta/subdomínio e plano de impacto zero; seguir o gate de aprovação aplicável ao servidor compartilhado.
- Nenhuma ação deve alcançar produção, credenciais, instância Evolution, backups preexistentes, volumes ou serviços de terceiros. Não usar prune ou `docker compose down` sem escopo.
