# Prévias protegidas de mídia

## O que é armazenado

- O JPEG importado fica em `media-source`, volume Docker privado e exclusivo do projeto `markina-gallery`.
- O worker cria em `media-derivatives` somente `thumbnail`, `client_preview` e `admin_preview` para cada foto.
- Nenhum desses paths é aceito do navegador, publicado pelo Nginx ou servido pelo Google Drive. O Drive permanece destinado a cópia/arquivo frio, não à entrega web.
- RAWs não são aceitos neste fluxo. Os derivados são JPEG e são gravados sem EXIF/GPS.

## Proteção e acesso

- A prévia da cliente recebe marca d'água incorporada ao bitmap; não é uma camada removível no navegador.
- A prévia do fotógrafo não recebe marca, mas tem limite de 2.000 px de largura e não é o original.
- Cada entrega exige sessão ativa. A cliente precisa estar vinculada à galeria derivada e à foto; o fotógrafo precisa ter papel administrativo.
- As respostas usam `Cache-Control: private, no-store`, não oferecem URL de arquivo persistente e registram auditoria de visualização.
- Captura de tela não pode ser tecnicamente impedida. A marca e os controles reduzem exposição, mas não substituem termos de uso ou orientação ao cliente.

## Capacidade e retenção

- Os volumes `media-source` e `media-derivatives` são criados com o prefixo do projeto Compose (por exemplo, `markina-gallery_media-source`), separados de banco, Redis e de outros projetos do servidor.
- Antes de homologar ou produzir, registrar o espaço livre do host e o tamanho dos dois volumes. O lote deve ser interrompido se não houver espaço suficiente para o JPEG de origem e seus três derivados.
- A política de retenção de originais e derivados ainda precisa ser definida pelo fotógrafo antes de qualquer limpeza automática. Até essa decisão, não há rotina de exclusão.
- Em qualquer manutenção, usar somente `docker compose -p markina-gallery -f docker/docker-compose.yml`; nunca executar `prune` nem remover volumes de outro projeto.

## Operação segura

1. Importar somente JPEG pela API administrativa; ela cria um job durável de processamento.
2. O worker exclusivo processa um job por vez e pode reprocessar a mesma foto sem criar caminhos duplicados.
3. Se uma prévia falhar, a interface mostra indisponibilidade; não se deve expor o original como alternativa.
4. Antes de alterar o servidor de homologação, fazer inventário de containers, portas, redes e volumes e apresentar o plano de impacto zero para aprovação.

Este documento não contém imagens reais, credenciais ou valores de ambiente.
