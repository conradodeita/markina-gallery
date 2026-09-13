import { ImageResponse } from "next/og";

export async function GET(_request: Request, { params }: { params: Promise<{ size: string }> }) {
  const { size: value } = await params;
  if (!["180", "192", "512"].includes(value)) return new Response(null, { status: 404 });
  const size = Number(value);
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#191816" }}>
      <svg width={size * .7} height={size * .7} viewBox="0 0 100 100">
        <rect x="4" y="4" width="92" height="92" rx="22" fill="none" stroke="#f2c343" strokeWidth="3" />
        <path d="M25 73V29L50 55L75 29V73" fill="none" stroke="#f2c343" strokeWidth="9" strokeLinejoin="round" />
        <circle cx="77" cy="20" r="5" fill="#f7f5ef" />
      </svg>
    </div>,
    { width: size, height: size, headers: { "Cache-Control": "public, max-age=86400" } },
  );
}
