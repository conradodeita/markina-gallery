"use client";

import { useEffect, useState } from "react";

import styles from "./folder-deadline-fields.module.css";

type RecoveryPricing = {
  recovery_fee_credits: number | null;
  configured: boolean;
  owner_exempt: boolean;
};

type FolderDeadlineFieldsProps = {
  mode?: "creation" | "existing";
  startsAt: "release" | "save";
  initialDays?: number | null;
};

export function FolderDeadlineFields({ mode = "creation", startsAt, initialDays }: FolderDeadlineFieldsProps) {
  const [recoveryPricing, setRecoveryPricing] = useState<RecoveryPricing | null>(null);

  useEffect(() => {
    if (mode !== "creation") return;

    const controller = new AbortController();
    void fetch("/api/admin/media-archive/recovery-pricing", {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error("Preço indisponível");
      const payload = await response.json() as Partial<RecoveryPricing>;
      const validFee = payload.recovery_fee_credits === null
        || (Number.isSafeInteger(payload.recovery_fee_credits) && Number(payload.recovery_fee_credits) > 0);
      if (typeof payload.configured !== "boolean" || typeof payload.owner_exempt !== "boolean" || !validFee) {
        throw new Error("Preço indisponível");
      }
      setRecoveryPricing(payload as RecoveryPricing);
    }).catch(() => {
      // O estado interno da configuração não é conteúdo para o fotógrafo.
    });
    return () => controller.abort();
  }, [mode]);

  return (
    <fieldset className={styles.fields}>
      <legend>Prazo para escolher fotos</legend>
      <label className={styles.daysLabel}>
        <span>Dias de acesso</span>
        <span className={styles.daysControl}>
          <input
            aria-label="Dias de acesso da pasta"
            name="access_duration_days"
            type="number"
            min={1}
            step={1}
            inputMode="numeric"
            placeholder="30"
            defaultValue={initialDays ?? ""}
            required
          />
          <span className={styles.daysSuffix}>dias</span>
        </span>
      </label>
      {mode === "creation" ? <p className={styles.guidance}>
        A contagem começa quando as fotos da pasta forem liberadas. Após a expiração, a pasta pode ir para o arquivo frio depois de 30 dias.
      </p> : startsAt === "save" ? <p className={styles.guidance}>A contagem começa hoje, quando você salvar este prazo.</p> : null}
      {mode === "creation" && recoveryPricing?.configured && recoveryPricing.recovery_fee_credits !== null ? (
        <p className={styles.pricing}>
          {recoveryPricing.owner_exempt
            ? <>Taxa de referência: <strong>{recoveryPricing.recovery_fee_credits} créditos por pasta e ciclo</strong>. Na sua conta, a recuperação não debita créditos.</>
            : <>Taxa atual: <strong>{recoveryPricing.recovery_fee_credits} créditos por pasta e ciclo</strong>. O débito ocorre após a recuperação completa e verificada; o valor pode mudar até lá.</>}
        </p>
      ) : null}
    </fieldset>
  );
}
