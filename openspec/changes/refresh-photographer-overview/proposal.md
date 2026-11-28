# Proposal

## Why

A direção Dourado Claro aprovada no Stitch reúne navegação, ações e indicadores em uma única composição. A Visão Geral é o primeiro recorte funcional dessa direção no painel autenticado do fotógrafo.

## What Changes

- Aplicar ao `/admin` a navegação lateral, o cabeçalho com busca de galerias e aparência, o fundo contínuo e a hierarquia da tela de referência.
- Organizar os cinco indicadores existentes em duas linhas no desktop, seguidos pelas etapas de publicação, galerias recentes, seleções e carteira.
- Preservar os atalhos existentes, o escopo da conta autenticada e os estados independentes da carteira. Adaptar a navegação para celular e teclado.
- Estender essa estrutura aos catálogos autenticados de Galerias e Clientes conforme suas referências no Stitch, com busca, apresentação responsiva dos registros e ações existentes.

## Capabilities

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: navegação e apresentação responsiva da Visão Geral do fotógrafo.

## Impact

Estrutura visual de `/admin`, `/admin/galleries` e `/admin/clients`, adaptada com estilos e fontes locais. Endpoints e permissões existentes são reutilizados. Editor de galeria, upload, checkout e pagamentos seguem em incrementos próprios.
