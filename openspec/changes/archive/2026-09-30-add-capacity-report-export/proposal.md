# Proposal

## Why

O painel de capacidade já apresenta um snapshot sanitizado e classificado por tipo de evidência, mas hoje o administrador precisa transcrever os valores ou recorrer a capturas de tela para solicitar uma análise externa. Esse processo favorece erros, perde contexto operacional e dificulta preservar informações essenciais como unidade, escopo, horário da coleta, cobertura, limitações e motivos de indisponibilidade.

## What Changes

- Adicionar ao diagnóstico administrativo a ação explícita **Copiar relatório**, disponível somente após uma coleta válida e autorizada.
- Gerar um relatório textual determinístico e sanitizado a partir do mesmo snapshot já exibido, sem nova coleta, persistência, envio de rede ou inclusão de dados ocultos.
- Incluir no relatório a versão do formato e do contrato, o horário UTC da coleta, o estado do cache, o escopo, os limites e o uso do pool da API, as conexões do PostgreSQL, as cinco classes de fila, unidades, fontes, tipos de evidência, cobertura, limitações e lacunas do orçamento global.
- Preservar explicitamente valores `unavailable`, seus motivos e a distinção entre evidência observada, calculada e estimada; nenhum valor desconhecido será convertido em zero ou apresentado como fato observado.
- Exibir retorno acessível de sucesso ou falha da cópia, sem remover o snapshot quando a API de área de transferência não estiver disponível.
- Documentar o formato e cobrir a serialização, a sanitização e os estados de autorização e erro com testes direcionados.
- Manter fora deste recorte a visão por fotógrafo, histórico, alertas, atualização automática, download de arquivo e envio automático do relatório para serviços externos.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations/admin-capacity-diagnostics`: acrescentar uma representação textual copiável, sanitizada e fiel ao snapshot administrativo atual, preservando sua semântica de evidência, cobertura e limitações.

## Impact

A mudança afeta o componente administrativo de capacidade no frontend, seus testes e a documentação operacional. O contrato existente de leitura será reutilizado sem novo endpoint, migration, tabela, dependência de infraestrutura ou alteração de configuração sensível. O relatório permanecerá no navegador até a ação explícita do administrador e não criará histórico no produto.
