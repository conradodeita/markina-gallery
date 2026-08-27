"use client";

import Link from "next/link";
import { type ButtonHTMLAttributes, type ReactNode, useEffect } from "react";

export function MarkinaButton({ children, variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" }) {
  return <button className={`mk-button mk-button--${variant} ${className}`} {...props}>{children}</button>;
}

export function MarkinaLink({ href, children, variant = "primary", className = "" }: { href: string; children: ReactNode; variant?: "primary" | "secondary" | "quiet"; className?: string }) {
  return <Link className={`mk-button mk-button--${variant} ${className}`} href={href}>{children}</Link>;
}

export function StatusBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "danger" }) {
  return <span className={`mk-badge mk-badge--${tone}`}>{children}</span>;
}

export function SurfaceCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`mk-card ${className}`}>{children}</section>;
}

export function SystemState({ title, detail, tone = "empty" }: { title: string; detail: string; tone?: "empty" | "error" | "loading" }) {
  return <div className={`mk-state mk-state--${tone}`} role={tone === "error" ? "alert" : "status"}><strong>{title}</strong><p>{detail}</p></div>;
}

export function ConfirmDialog({ open, title, detail, confirmLabel, onConfirm, onCancel }: { open: boolean; title: string; detail: string; confirmLabel: string; onConfirm: () => void; onCancel: () => void }) {
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onCancel(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onCancel, open]);
  if (!open) return null;
  return <div className="mk-dialog-backdrop" role="presentation"><section aria-describedby="confirm-detail" aria-labelledby="confirm-title" aria-modal="true" className="mk-dialog" role="dialog"><p className="eyebrow">Confirmação necessária</p><h2 id="confirm-title">{title}</h2><p id="confirm-detail">{detail}</p><div className="mk-dialog__actions"><MarkinaButton variant="secondary" onClick={onCancel}>Cancelar</MarkinaButton><MarkinaButton onClick={onConfirm}>{confirmLabel}</MarkinaButton></div></section></div>;
}
