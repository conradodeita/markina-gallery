## Decisions

1. Retirar o seletor de pasta global, suas duas rotas na API e suas mensagens no Console. Manter o componente de conexão OAuth e o estado da conexão e da quota.
2. Desativar os três workflows exclusivos e retirar os segredos SSH de uso exclusivo em GitHub Actions. Manter o canal de suporte compartilhado para os releases da aplicação.
3. No servidor, delimitar o conjunto ao serviço e ao timer inativos e aos seus diretórios próprios. Confirmar mounts, dependências, artefatos e permissões antes da retirada. Retirar a configuração montada do Picker somente após retirar seu bind da API pelo fluxo de publicação. Identificar a chave de navegador e a entrada SSH dedicada por evidência de identidade. Validar saúde, schema inalterado e continuidade da aplicação e dos outros projetos.
4. No Drive e na recuperação offline, verificar a origem e a exclusividade de cada cópia e chave antes de excluir. A pasta do timer compartilhado, os dados ativos, a conexão OAuth da plataforma e as cópias de rollback de outros fluxos ficam protegidos. Manter recibos sanitizados da retirada.
5. Usar o histórico Git como registro do experimento. O novo plano substitui a tentativa e terá sua própria change.
