# Fontes locais

As fontes abaixo são empacotadas no build por dependências Fontsource fixadas em `5.3.0`. O navegador recebe arquivos WOFF2 pelo mesmo domínio da Markina Gallery e não consulta Google Fonts ou outro serviço externo.

- Montserrat Variable — Copyright 2011 The Montserrat Project Authors.
- Playfair Display Variable — Copyright 2017 The Playfair Display Project Authors; “Playfair Display” é nome reservado.
- Caveat Variable — Copyright 2014 The Caveat Project Authors.
- Dancing Script Variable — Copyright 2016 The Dancing Script Project Authors; “Dancing Script” é nome reservado.

Todas são distribuídas sob a SIL Open Font License 1.1. O texto integral está versionado em `licenses/OFL-1.1.txt`; a versão, integridade e licença declarada de cada pacote ficam registradas em `package-lock.json`.

O bundle importa somente um WOFF2 variável latino, normal, por família. Isso cobre português e os pesos expostos pela interface sem enviar subconjuntos cirílicos, vietnamitas, `latin-ext` ou itálicos. Os arquivos são resolvidos das dependências fixadas durante o build e servidos pelo próprio domínio.

SIL Open Font License 1.1: é concedida permissão gratuita para usar, estudar, copiar, mesclar, incorporar, modificar e redistribuir a fonte, desde que ela não seja vendida isoladamente, que o aviso de copyright e a licença acompanhem cada cópia, que nomes reservados não sejam usados por versões modificadas sem permissão, e que a fonte permaneça sob a mesma licença. O software é fornecido “no estado em que se encontra”, sem garantias.
