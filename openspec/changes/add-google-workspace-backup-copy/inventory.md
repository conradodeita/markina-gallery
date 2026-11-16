# Inventário e roteiro pré-abertura — backup Google Workspace

## Estado desta preparação

- API Google Drive: ativada pelo proprietário no projeto Pick-your-Pic; não revalidada nesta execução.
- Cliente OAuth web: criado pelo proprietário; JSON, segredo e tokens não foram lidos nem copiados nesta execução.
- Destino: Google Workspace da organização do proprietário; quota, edição, Shared Drive, pasta e permissões efetivas continuam sem medição autenticada.
- Identidades: conta do proprietário somente para o ensaio pré-abertura; identidade Workspace dedicada e independente para a rotina recorrente.
- Código local: transporte sintético; nenhuma chamada ou gravação foi feita no Google Drive.
- Produção: nenhuma leitura, configuração, publicação ou alteração operacional foi feita.

## Pré-requisitos do ensaio real com o proprietário

- [ ] Release autorizado em janela com inventário de serviços, imagens/SHA, migrations, portas e plano de impacto zero.
- [ ] Serviço/instância de origem e revisão de schema anotados sem dados de cliente.
- [ ] Consentimento OAuth do aplicativo e conexão owner-only confirmados; verificar o scope efetivo `drive.file`.
- [ ] Pasta dedicada de ensaio, privada e acessível pelo aplicativo; anotar somente IDs internos necessários em local operacional protegido.
- [ ] Confirmar quota via consulta autenticada; não tomar “aproximadamente 100 TB” como quota observada.
- [ ] Se usar Shared Drive, confirmar edição Workspace, membership e permissões de leitura/escrita; busca deverá usar o `driveId` exato.
- [ ] Preparar destino restaurável descartável, isolado, vazio e atômico, sem apontar para containers/volumes de clientes ou de outros projetos.
- [ ] Produzir backup global cifrado; registrar UUID, SHA-256, tamanho e hora UTC em evidência sanitizada.
- [ ] Enviar, ler de volta, comparar ciphertext, autenticar GCM, manifesto e schema; restaurar no destino descartável.
- [ ] Registrar restore verificado e resultado, sem dump, configuração em claro, URL de sessão ou segredo.
- [ ] Revogar/desconectar a identidade owner-only após o ensaio, preservando a evidência e o artefato conforme retenção aprovada.

## Pré-requisitos da rotina recorrente

- [ ] Identidade Workspace dedicada criada pelo proprietário/administrador da organização, separada da conta pessoal do proprietário e sem usar service account.
- [ ] Identidade submetida ao mínimo privilégio necessário na pasta dedicada de rotina; nenhuma permissão pública ou link compartilhável.
- [ ] OAuth autorizado pelo proprietário enquanto autenticado no painel; refresh token permanece cifrado no mecanismo já existente.
- [ ] Quota, destino, pasta pai e permissões da identidade dedicada confirmados por consulta autenticada.
- [ ] Worker/scheduler produtivo, origem confiável e cópia recorrente liberados por change/release próprio e autorização operacional.
- [ ] Cópia cifrada sintética ou de snapshot aprovado enviada e lida de volta; checksum e autenticação validados sem expor plaintext.
- [ ] Próximo ciclo agendado observado e confirmado no catálogo autenticado, com erros sanitizados.

## Gate para abrir o cadastro público

Manter onboarding público fechado até o proprietário revisar as evidências sanitizadas do restore feito com sua conta, da rotina recorrente testada com a identidade dedicada, da quota e das permissões efetivas. Esta preparação não autoriza OAuth real, chamadas Google, escrita remota, deploy, migration, expurgo ou abertura a tenants.
