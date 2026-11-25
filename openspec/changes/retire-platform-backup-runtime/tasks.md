## 1. Interromper a operação antiga

- [x] 1.1 Desativar os workflows exclusivos de runtime, instalador do wrapper e configuração do Picker. Remover os dois segredos `PRODUCTION_BACKUP_SSH_*` do ambiente GitHub `production` e confirmar a ausência.
- [x] 1.2 Retirar o seletor da UI, as rotas de autorização global e seus testes exclusivos. Validar Console e OAuth compartilhado. Classificar a retirada como protegida para impedir publicação automática no mesmo delta que as mudanças pendentes de mídia.
- [ ] 1.3 Retirar do repositório o código operacional exclusivo e as referências ativas após confirmar seus consumidores. Preservar recibos históricos, funções de arquivo de mídia e suporte compartilhado.

## 2. Retirar os recursos instalados

- [ ] 2.1 Inventariar a operação, o bind da API e as dependências de cada credencial. Delimitar a publicação e a retirada do runtime no canal autorizado.
- [ ] 2.2 Retirar unidades, releases, configurações e credenciais exclusivas no host e no Google Cloud. Verificar saúde da aplicação e ausência dos itens retirados.
- [ ] 2.3 Localizar e retirar cópias, chaves e pasta de ensaio dedicadas no Drive e em mídia offline. Registrar itens cujo vínculo ou acesso ainda exija confirmação.

## Evidências de 25/11/2026

- GitHub confirmou a desativação dos três workflows dedicados e a ausência dos dois segredos SSH específicos do runtime após a retirada.
- Na inspeção somente de leitura, o serviço estava inativo e o timer inativo e desabilitado. Foram observadas quatro entradas de release, as três configurações do runtime e a configuração do Picker. O diretório de trabalho não foi localizado, e o diretório de configuração não continha journals de ensaio. O domínio `markina.pickyourpic.com.br` respondeu HTTP 200 em `/`, `/healthz` e `/api/health`.
- A custódia anterior registra uma chave offline dedicada em `D:`. A unidade estava indisponível na estação durante o inventário.
- Uma API ativa estava montando a configuração do Picker. O proxy publica a aplicação em `127.0.0.1:8080` e o acesso público HTTPS usa o domínio registrado acima. A liberação da nova API e a retirada do mount precedem a exclusão do arquivo do Picker.
- Sete testes do Console, build com TypeScript, lint do frontend tocado e 41 testes de OAuth e inventário em ambiente sintético passaram localmente. O pacote retira os três arquivos de workflow exclusivos. O manifesto histórico de produção mantém seus pins até nova análise do delta contra a versão ativa.
