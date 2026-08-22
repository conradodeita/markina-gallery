import { NextResponse } from "next/server";

// Health check usado pelo Docker Compose (healthcheck) e pelo Nginx.
// Nenhuma outra rota existe neste scaffolding.
export function GET() {
  return NextResponse.json({ status: "ok", service: "web" });
}
