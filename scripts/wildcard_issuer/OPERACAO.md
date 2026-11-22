# Operação local do emissor wildcard

## Estado e escopo

Este pacote prepara a emissão e instalação de um certificado `*.pickyourpic.com.br` por ACME/DNS-01, com DNS Cloudflare. A implementação e as evidências desta change são locais e sintéticas. **Não copiar nem aplicar estes arquivos no Oracle sem autorização específica do proprietário para a operação concreta.** O certificado, a chave, o token DNS, o ID de conta ACME e os arquivos de aprovação ainda não existem no pacote.

O registro DNS wildcard e o NPM compartilhado pertencem a operações anteriores. Este pacote não os altera. Os templates systemd não têm seção `[Install]`; copiar um template não inicia nem habilita o emissor, helper, socket ou timer. A emissão usa o endpoint ACME de produção do Let's Encrypt e pode criar/remover registros TXT por meio da API Cloudflare; portanto, a execução real exige autorização separada e confirmação de zona, escopo do token, e-mail e termos da CA.

## Componentes e identidades

- O grupo `pyp-acme` é a fronteira do socket local. O usuário `pyp-acme` executa Certbot e não deve pertencer ao grupo `docker` nem conseguir abrir o socket Docker.
- `pyp-acme-installer.service` executa como root apenas por precisar chamar comandos fixos de Docker e alterar os arquivos do certificado no NPM aprovado. Esse é um componente privilegiado de alto impacto; sua instalação requer revisão integral de código, caminhos, hash da imagem, ID imutável do container, binds e hash de cada arquivo interno.
- O emissor recebe a chave do envelope por `LoadCredential=` do systemd 249. A chave fonte é root-only e não é criptografada por essa diretiva. O cofre AES-GCM pertence a `pyp-acme`, em `/var/lib/pyp-acme-issuer/vault`; a chave e o cofre devem permanecer em custodias e cópias de recuperação separadas.
- O token Cloudflare fica cifrado no cofre. O arquivo INI temporário é criado em `/run/pyp-acme-issuer`, modo `0600`, usado por caminho fixo e apagado ao terminar, inclusive após falha. Token não pode ir para linha de comando, ambiente, logs, unidade, backup em claro ou saída de suporte.

## Preparação autorizada antes de qualquer aplicação externa

1. Rever o relatório local `validation.md`, o lock ARM64, licenças, hashes, avisos de segurança e a revisão do código. Confirmar que a fonte e o digest do NPM ainda correspondem ao pacote.
2. Fazer inventário remoto atualizado sem alterações: unidades, usuários/grupos, versão do systemd, Docker, ID/digest do NPM, portas, volumes, bind mounts, espaço, certificados e probes dos hosts raiz e `markina`.
3. Definir, sem enviar no chat, quem custodiará a chave mestra e sua cópia offline; preparar recuperação e testar a restauração antes de guardar qualquer token real. Uma cópia da chave sem o cofre e um cofre sem a chave devem ser inúteis isoladamente.
4. Obter um token Cloudflare dedicado, limitado à edição DNS da zona `pickyourpic.com.br`; não usar Global API Key. O token deve ser entregue pelo mecanismo local aprovado, nunca por argumento, ambiente, Git ou mensagem.
5. Fixar e revisar o ID da conta ACME e o texto/aceite dos termos pelo proprietário. Nenhum comando do pacote registra automaticamente uma conta nem aceita termos.
6. Revisar hash, dono, grupo, modo, caminho e conteúdo de cada arquivo no manifesto operacional final. Conferir novamente que todas as unidades e timers estão inativos e não habilitados.
7. Apresentar plano de impacto zero, probe inicial, duração estimada, critérios de interrupção e retorno. Se for necessário parar, reiniciar, recriar ou substituir NPM, proxy, host, rede, volume, firewall ou serviço existente, não prosseguir sem autorização específica para essa interrupção.

## Validação das unidades e instalação futura

O ensaio local usa `systemd-analyze verify` no systemd 249 e permissões Linux reais. Em Windows, arquivos da pasta do projeto podem aparecer como executáveis ou graváveis por todos quando bind-mounted; isso gera avisos que não representam os modos Unix esperados. Na instalação futura, os templates devem ser copiados para diretório root-owned, sem links, modo `0644`; configurações públicas root-owned e somente leitura; chave fonte root-owned `0400`; diretório da chave `0700`; cofre e runtime pertencentes a `pyp-acme`, ambos `0700`; token materializado `0600`.

Instalar somente os arquivos e paths listados no manifesto aprovado. Criar usuários, grupos, diretórios, `issuer.json`, `installer.json`, trust store e chave requer uma operação aprovada separadamente. Não iniciar o socket ou o serviço helper antes de verificar a identidade e o hash exato do NPM e da imagem que receberá o certificado. O gateway deve verificar o container antes de cada instalação e recusar qualquer alteração.

O primeiro uso aprovado é uma emissão única iniciada manualmente, com os probes raiz e `markina` saudáveis antes e depois. O timer permanece desativado. Somente após demonstrar renovação, retorno e monitoramento, o proprietário pode decidir se autoriza agendamento. O agendamento não deve ser habilitado implicitamente pela instalação.

## Falha, validade e alertas

O pacote não envia e-mail, WhatsApp, métrica ou alerta externo. Até que uma integração de monitoramento seja aprovada e implementada, a operação depende de verificação manual documentada:

- consultar o resultado sanitizado do emissor e do helper e o estado das units;
- inspecionar a validade e o SAN do certificado instalado sem imprimir nem copiar a chave privada;
- verificar os probes TLS/SNI e HTTP dos hosts raiz, `markina` e de um subdomínio wildcard sintético aprovado;
- agir antes do vencimento; falha de renovação não autoriza remoção do certificado ainda saudável nem reinício do proxy.

Não coletar `journalctl` bruto para suporte antes de confirmar que o conteúdo não inclui credenciais. Erros deste pacote devem ser reportados pelo código sanitizado; o diagnóstico de segredo fica restrito ao operador autorizado.

## Recuperação, rotação e remoção

Para recuperar, restaurar a chave root-only e o cofre em separado, verificar proprietário, modos, número de links e hashes e testar a decifragem sem imprimir valores. Chave ausente/incorreta ou cofre corrompido significa falha fechada: não emitir nem instalar. Após rotação, testar a nova chave e o novo envelope; manter a cópia offline anterior até a restauração da cópia nova ser demonstrada. Nunca colocar a chave junto ao backup diário que contém o cofre.

Para remover futuramente o emissor, interromper primeiro novas execuções e o agendamento apenas sob autorização operacional explícita; confirmar que nenhuma emissão/instalação está ativa; preservar a configuração, o cofre e a chave aprovados até decidir a retenção. Remover somente arquivos e unidades pertencentes a este pacote e aprovados na operação. Não apagar automaticamente o certificado que esteja em uso, diretórios ou certificados preexistentes do NPM, nem reiniciar ou parar serviços compartilhados. Qualquer descarte de segredo requer inventário, custódia/recuperação aprovada e autorização própria.

## Limites da prova local

As provas cobrem mecanismos locais com valores, certificados, NPM e UIDs sintéticos; não provam propagação DNS, emissão pública, credenciais Cloudflare, conta Let's Encrypt, atual configuração remota, disponibilidade do proxy compartilhado, processo de expiração nem restauração em Oracle. A preparação não é um sinal verde para deploy.
