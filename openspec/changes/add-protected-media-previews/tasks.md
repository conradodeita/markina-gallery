## 1. Derivados e processamento

- [x] 1.1 Criar migration aditiva para metadados de derivados e jobs de mídia, verificando upgrade e downgrade em banco sintético.
- [ ] 1.2 Implementar importação local de JPEG e geração idempotente de miniatura, prévia protegida e prévia administrativa, verificando dimensões, ausência de EXIF/GPS e ausência de exposição do original.
- [ ] 1.3 Configurar fila e volume exclusivo da Markina para processamento de mídia, verificando que paths e jobs não alcançam recursos de outros projetos.

## 2. Entrega autorizada e interface

- [ ] 2.1 Implementar endpoints de prévia por papel e galeria derivada, verificando cliente autorizado, admin, acesso cruzado e inexistência de URL pública persistente.
- [ ] 2.2 Implementar visualizador ampliado responsivo para cliente e fotógrafo, verificando estados carregando, indisponível e navegação por teclado.
- [ ] 2.3 Integrar previews protegidos ao histórico de compras e à conferência administrativa, verificando que cliente não recebe a variante administrativa.

## 3. Segurança e operação

- [ ] 3.1 Cobrir processamento idempotente, remoção de metadados, marca incorporada, autorização e auditoria com testes automatizados.
- [ ] 3.2 Validar lint, build, migration e homologação com imagens sintéticas, incluindo inventário de volume e plano de impacto zero antes de alteração no servidor.
- [ ] 3.3 Atualizar documentação de capacidade, retenção, proteção visual e limites conhecidos de captura de tela, verificando que não há imagens ou segredos reais versionados.
