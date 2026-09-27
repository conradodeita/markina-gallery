"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { SystemState } from "../../ui-kit";

export default function LegacyGalleryRedirect() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/gallery/${galleryId}`, {
      credentials: "same-origin",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Acesso indisponível");
        const result: { redirect_url?: string } = await response.json();
        if (!result.redirect_url) throw new Error("Destino indisponível");
        router.replace(result.redirect_url);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [galleryId, router]);

  return failed ? (
    <main className="client-page">
      <SystemState title="Galeria indisponível" detail="Não foi possível abrir este acesso. Volte à sua coleção ou consulte Compras." />
      <a href="/library">Ver coleção</a>
      <a href="/library/purchases">Ver compras</a>
    </main>
  ) : (
    <main className="client-page" role="status">Abrindo sua coleção…</main>
  );
}
