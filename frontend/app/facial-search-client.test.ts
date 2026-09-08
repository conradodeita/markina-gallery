import { afterEach, describe, expect, it, vi } from "vitest";

import { FacialApiError, facialAdminApi, facialSearchApi } from "./facial-search-client";

afterEach(() => vi.restoreAllMocks());

describe("contratos HTTP faciais", () => {
  it("envia somente JPEG e recibo explícito ao criar consulta", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "request-1" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["jpeg"], "rosto.jpg", { type: "image/jpeg" });

    await facialSearchApi.create("gallery-1", file, "consent-v1", "adult");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/gallery-1/facial-searches",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        body: file,
        headers: expect.objectContaining({
          "content-type": "image/jpeg",
          "x-facial-consent-version": "consent-v1",
          "x-facial-subject-declaration": "adult",
        }),
      }),
    );
  });

  it("mantém request, galeria e foto no escopo das mutations", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await facialSearchApi.read("gallery-1", "request-1");
    await facialSearchApi.cancel("gallery-1", "request-1");
    await facialSearchApi.reject("gallery-1", "request-1", "photo-1");
    await facialSearchApi.select("gallery-1", "request-1", "photo-1");
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      "/api/public-galleries/gallery-1/facial-searches/request-1",
      "/api/public-galleries/gallery-1/facial-searches/request-1",
      "/api/public-galleries/gallery-1/facial-searches/request-1/candidates/photo-1",
      "/api/public-galleries/gallery-1/facial-searches/request-1/candidates/photo-1/selection",
    ]);
  });

  it("envia a confirmação versionada do responsável somente na consulta infantil", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "request-1" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["jpeg"], "crianca.jpg", { type: "image/jpeg" });

    await facialSearchApi.create(
      "gallery-1",
      file,
      "consent-v1",
      "minor",
      "guardian-self-declaration-v1",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/gallery-1/facial-searches",
      expect.objectContaining({
        headers: expect.objectContaining({
          "x-facial-subject-declaration": "minor",
          "x-facial-representation-reference": "guardian-self-declaration-v1",
        }),
      }),
    );
  });

  it("recupera a busca mais recente da cliente autenticada", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "request-latest" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await facialSearchApi.latest("gallery-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/gallery-1/facial-searches/latest",
      { credentials: "same-origin" },
    );
  });

  it("preserva status e Retry-After em indisponibilidade temporária", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: "Busca temporariamente indisponível." }),
      { status: 503, headers: { "Retry-After": "17" } },
    )));

    await expect(facialSearchApi.availability("gallery-1")).rejects.toEqual(
      expect.objectContaining<Partial<FacialApiError>>({
        status: 503,
        retryAfterSeconds: 17,
      }),
    );
  });

  it("envia somente IDs de jobs na retentativa administrativa", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ retried: 2 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await facialAdminApi.retry("gallery-1", ["job-1", "job-2"]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/gallery-1/facial-index/retry",
      expect.objectContaining({ body: JSON.stringify({ job_ids: ["job-1", "job-2"] }) }),
    );
  });
});
