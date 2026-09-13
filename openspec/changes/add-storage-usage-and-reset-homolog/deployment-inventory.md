## Inventário de publicação e impacto zero

### Alvo autorizado

- Ambiente: homologação privada.
- Repositório esperado: `conradodeita/markina-gallery`.
- SHA-base validado antes da change: `b3b22b02ce77ae60b8e252e4046d1387d9e836c5`.
- Checkout remoto literal: `/opt/markina-gallery`.
- Projeto Docker Compose: `markina-gallery`.
- Entrada exclusiva no host: `127.0.0.1:8080`.
- Subdomínio: `https://markina-homolog.duckdns.org`.
- Environment protegido: `homolog`.

O SHA-alvo será o merge commit publicado pelo workflow e ficará registrado no log
imutável do GitHub Actions e no marcador de revisão do servidor.

### Último inventário agregado disponível

O deploy verde do SHA-base, execução GitHub Actions `34696828718`, registrou em
2026-09-12, sem PII:

- 3 galerias públicas, 2 galerias privadas, 1 cliente e 825 fotos;
- 2 registros públicos, 2 associações privadas, 6 seleções e 3 pedidos;
- 1 comunicação de pagamento, 12 sessões de cliente, 12 desafios OTP de cliente
  e 15 entregas WhatsApp operacionais;
- origem: 825 arquivos e 535.013.335 bytes;
- derivados: 2.475 arquivos e 721.177.772 bytes;
- histórico: 0 arquivos e 0 bytes;
- total físico fotográfico conhecido: 1.256.191.107 bytes (aprox. 1,17 GiB).

O inventário autoritativo será repetido automaticamente depois de pausar somente
os serviços Markina que podem escrever nesses dados e imediatamente antes da
mutação. Diferenças desde o inventário acima serão preservadas no log do deploy.

### Plano de impacto zero

1. CI valida backend, frontend, segredos e OpenSpec; o Environment `homolog`
   continua exigindo aprovação.
2. O deploy fixa o SHA no checkout literal e mantém `FACIAL_PROCESSING_ENABLED=true`.
3. Somente `api`, `worker` e os workers faciais Markina ativos são pausados; `web`,
   banco e Redis exclusivos permanecem sob o mesmo projeto Compose.
4. O trailer exclusivo seleciona conjuntamente modo `execute`, flag
   `--without-backup` e token
   `DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP`. Qualquer combinação
   incompleta aborta antes da exclusão.
5. Nenhum novo dump é criado, conforme dispensa explícita do proprietário; backups
   preexistentes não são alterados.
6. A rotina limita a mutação ao PostgreSQL, Redis e às três raízes de mídia da
   Markina Gallery. Não usa prune, `docker compose down`, remove-orphans, proxy,
   firewall, DNS, certificados, redes, volumes ou containers de terceiros.
7. O pós-check exige contagens operacionais e bytes zerados, igualdade das
   contagens preservadas de admin/sessões/fatores/preferências, saúde de web/API e
   workers configurados e coerência da flag facial.

### Recuperação

Os dados de teste removidos não terão backup novo nem restauração fornecida por
esta execução. Rollback de código não recupera galerias, clientes ou mídia
apagados. Essa consequência foi explicitamente aceita pelo proprietário.

### Evidência da execução autorizada

- Publicação destrutiva: merge `d8664a3f0b2e23fbeb9387184454a279d264f415`,
  execução GitHub Actions `34726883948`, concluída com sucesso pelo trailer
  exclusivo `Homolog-Cleanup: galleries-and-clients-without-backup` e sem criar
  backup novo.
- Inventário imediatamente anterior: 3 galerias públicas, 2 galerias privadas,
  8 pastas, 1 cliente, 825 fotos, 6 seleções e 3 pedidos; 825 arquivos de origem
  (535.013.335 bytes), 2.475 derivados (721.177.772 bytes) e histórico vazio.
- Inventário posterior: todas as contagens operacionais ficaram em zero e as
  raízes `source`, `derivatives` e `history` ficaram com zero arquivo e zero byte.
- Contagens preservadas antes/depois: 1 conta admin, 39 sessões admin, 2 desafios
  de segurança admin, 1 configuração de marca, 1 configuração PIX global,
  0 templates de pagamento, 2 presets de preço e 1 configuração WhatsApp.
- Correção operacional: merge
  `b56c049a52b75c7f53b8f9c833b4894e2f0cde1c`, execução GitHub Actions
  `34727732372`, para recarregar o Nginx Markina após a recriação da API e exigir
  o healthcheck HTTP externo ao Compose nas próximas manutenções.
- Verificação final em 2026-09-13: inventário novamente zerado, contagens
  preservadas inalteradas, todos os serviços configurados saudáveis,
  `FACIAL_PROCESSING_ENABLED=true`, `/api/health` com HTTP 200 e `/admin` com
  HTTP 200. O build publicado contém o card `Armazenamento de fotos` e seus
  contratos backend/frontend passaram no CI.
