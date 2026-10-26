# Arquivo: compatibilidade do antigo pipeline RAW

Em 26/10/2026, a change `retire-lightcraft-and-gemma` aposentou o intake RAW e o LightCraft. O código de upload/conversão e a interface foram removidos; o fluxo atual aceita JPEG. Este documento é somente histórico e não deve ser usado para configurar ou publicar workers RAW.

As migrations históricas `20260911_0078` e `20260912_0079`, seus registros e as referências de staging na higienização de homologação foram mantidos para compatibilidade e preservação. Não foram apagados arquivos, configurações, volumes ou dados existentes. Qualquer runtime RAW ainda ativo exige inventário e parada operacional controlada antes de uma publicação que dependa da ausência desse worker.

O ajuste opcional de prévias para JPEG permanece ativo e usa RawTherapee 5.13; ele não recebe nem processa RAW.
