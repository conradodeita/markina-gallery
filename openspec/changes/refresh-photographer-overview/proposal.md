# Proposal

## Why

A direção Dourado Claro aprovada no Stitch reúne navegação, ações e indicadores em uma única composição. A Visão Geral é o primeiro recorte funcional dessa direção no painel autenticado do fotógrafo.

## What Changes

- Aplicar ao `/admin` a navegação lateral, o cabeçalho com busca de galerias e aparência, o fundo contínuo e a hierarquia da tela de referência.
- Organizar os cinco indicadores existentes em duas linhas no desktop, seguidos pelas etapas de publicação, galerias recentes, seleções e carteira.
- Preservar os atalhos existentes, o escopo da conta autenticada e os estados independentes da carteira. Adaptar a navegação para celular e teclado.
- Estender essa estrutura aos catálogos autenticados de Galerias e Clientes conforme suas referências no Stitch, com busca, apresentação responsiva dos registros e ações existentes.
- Clarear o fundo em Dourado Claro e manter a rolagem do editor de cliente dentro do próprio diálogo.
- Aplicar a direção a Vendas e pagamentos com os indicadores, filtros e ações financeiras existentes.
- Aplicar o visual de Nova galeria ao formulário inicial, com encaminhamento para as etapas existentes de configuração.

## Capabilities

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: navegação e apresentação responsiva da Visão Geral, catálogos e consulta financeira do fotógrafo.

## Impact

Estrutura visual de `/admin`, `/admin/galleries`, `/admin/galleries/new`, `/admin/clients` e `/admin/payments`, adaptada com estilos e fontes locais. Endpoints e permissões existentes são reutilizados. As etapas de edição, upload e checkout seguem em incrementos próprios.
