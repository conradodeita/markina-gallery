# Identidade visual persistente

Logo, favicon e ícone permanecem no volume exclusivo `markina-gallery_branding-assets`,
montado **somente na API** em `/var/lib/markina/branding`. O Compose define
`BRANDING_ASSETS_ROOT` para esse diretório. Fora de Docker permanece o fallback local
`media/branding`. Contratos, validação, limites atuais e URLs `/branding/*` não mudam.
Não há migration SQL, nova porta, alteração de fotos ou reconstrução automática de arte.

## Publicação e janela sem uploads

O deploy exige autorização/inventário conforme o procedimento do projeto. O script:

1. Faz backup lógico e constrói as imagens enquanto a API antiga continua atendendo.
2. Identifica API, banco e volume pelos labels exclusivos do projeto; recusa raiz,
   ownership, driver ou opções inesperadas. Não imprime variáveis de ambiente.
3. Encerra graciosamente **somente a API antiga**, impedindo uploads concorrentes.
   Durante essa janela curta, a API fica indisponível; frontend e terceiros não param.
4. Lê somente as três chaves de branding do banco e copia arquivos regulares válidos
   por nome/tamanho. Não extrai árvores, links simbólicos, fotos ou segredos.
5. Salva bytes e SHA-256 em diretório `branding-*` restrito dentro de
   `/var/lib/markina-gallery/backups`. A configuração do banco não é alterada.
6. O usuário proprietário lê seu backup restrito e envia somente manifesto/bytes por
   stdin ao helper, sem montar diretórios privados do host nem ampliar capabilities.
   O helper usa tmpfs limitado e conserva `cap-drop ALL`, rede desativada e raiz somente
   leitura. Transfere para o volume usando publicação atômica sem sobrescrita e verifica hashes.
   Destino igual permite repetição; divergência, symlink, falha de cópia ou integridade
   abortam antes de recriar a API. Na falha de preservação, a API antiga é reiniciada.
7. Mantém override próprio em `/var/lib/markina-gallery/deploy-state/branding.compose.yml`
   para conservar mount e variável mesmo ao voltar a um Compose anterior. Aplica
   migrations e recria os serviços. O worker opcional de prévias só é atualizado se
   já estava ativo; não é habilitado por este procedimento.

Ausência confirmada pela cópia Docker é registrada no manifesto como `missing` e
permite publicação dos demais ativos. Outros erros **não** são tratados como ausência.
Após persistência verificada, pedir reenvio dos arquivos individuais faltantes no painel;
um registro SQL/backup lógico não recupera bytes já perdidos. Nunca usar a prancha de
referência nem imagens sintéticas como substitutas da arte real.

## Backup e restauração de branding

Cada deploy inclui os arquivos atualmente referenciados, inclusive quando já estão no
volume. Manifesto e bytes são separados do dump SQL, em diretório com modo 0700 e arquivos
0600. Os backups não são apagados pelo script. O log informa o diretório exato e a lista
de ausências, sem dados pessoais. Escolha e inspecione **um caminho exato de backup**;
nunca use glob para restaurar nem importe um dump para recuperar apenas ícones.

Com autorização para restauração e API sem uploads concorrentes, use a mesma imagem
da API e a função `restore_volume` do helper `scripts/preserve_branding.py`, que lê o
backup como seu proprietário e o transmite por stdin, montando somente o volume de
destino. Não montar backup 0700 de outro UID em container root com capabilities removidas:
root sem DAC_OVERRIDE não pode lê-lo. Execute com rede desativada, raiz somente leitura,
tmpfs limitado e apenas o volume persistente gravável, como no helper de deploy.
Para diretórios locais isolados, permanece `restore <backup> <destino>`.
O helper verifica todos os hashes antes de copiar, recusa symlinks e não sobrescreve
arquivos divergentes. Para verificar sem tocar homologação, restaure primeiro em um
diretório/volume **novo e isolado**. Não remover conflitos automaticamente: registrar os
dois hashes e solicitar decisão humana sobre o arquivo a manter. Nenhuma restauração de
banco, fotos, preferências ou credenciais faz parte desse procedimento.

## Rollback

Usar o script versionado que conhece o override; um `compose up` manual com Compose
antigo, sem esse override, não é um rollback válido. Nunca remover o volume. Antes de
preservação bem-sucedida, o tratamento de erro não recria containers (a camada antiga
pode conter a única cópia). Depois de preservar, o rollback seguro mantém volume/raiz.
Se migration mudou o schema ou seu estado é incerto, a regra existente bloqueia rollback
automático de código/banco e exige revisão humana. Não apagar backups para contornar isso.

## Validação focada

- `python scripts/test_preserve_branding.py -v`: integridade, repetição, conflito,
  ausência, caminho inválido, symlink, erro de cópia e preservação do container antigo.
- Com Docker local: `BRANDING_DOCKER_TEST=1 python scripts/test_preserve_branding.py -v`.
  Cria volume aleatório `pick-branding-test-*`, recria containers isolados sem rede,
  compara hashes de três PNGs sintéticos e remove somente o volume exato da fixture.
- Testes de branding em `backend/tests/test_derived_galleries.py`: autorização,
  validação, leitura, tamanhos, preferências e fallback seguro.
- `bash scripts/test_deploy_homolog.sh`: ordem operacional, isolamento e gates.

Não confundir teste sintético com validação humana dos três arquivos reais enviados pelo
proprietário. A revisão humana permanece necessária antes de sincronizar/arquivar specs.
