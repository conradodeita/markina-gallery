# Inventário somente leitura de homologação — 2026-09-26

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
