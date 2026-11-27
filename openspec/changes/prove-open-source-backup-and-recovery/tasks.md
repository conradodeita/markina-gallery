## 1. Prova integrada em desenvolvimento

- [ ] 1.1 Provar cópia PostgreSQL cifrada, leitura de retorno e restauração em banco isolado. Registrar versão, duração e recuperação com chave externa.
- [ ] 1.2 Provar extração de um fotógrafo a partir da cópia global restaurada, com dois fotógrafos distintos e verificação de relações e ausência de dados cruzados.
- [ ] 1.3 Exercitar upload e solicitação de recuperação de uma pasta fria pelo aplicativo com dois fotógrafos sintéticos e o mesmo conjunto de ferramentas da cópia global. Verificar catálogo/isolamento, readback integral, exclusão por objeto e falha sem débito; preservar UI/fila existentes.
- [ ] 1.4 Validar prazo de elegibilidade de 30 dias, 30 dias fixos após nova recuperação do fotógrafo conforme `fix-cold-recovery-access-window`, taxa configurável por pasta/ciclo, reserva idempotente, débito só após disponibilização íntegra, liberação em falha, reserva em reconciliação incerta, isenção do proprietário e ausência de expurgo automático.
- [ ] 1.5 Registrar resultado único da prova, compatibilidade operacional dos mesmos componentes com restauração global e seletiva, retenção/exclusão por objeto, duração e escopo de implementação conjunta.
