import { AuthEntry } from "./auth-entry";

export default async function Home({ searchParams }: {
  searchParams: Promise<{ access_token?: string | string[]; return_to?: string | string[]; reauth?: string | string[] }>;
}) {
  const params = await searchParams;
  const accessToken = typeof params.access_token === "string" ? params.access_token : "";
  const returnTo = typeof params.return_to === "string" ? params.return_to : "";
  const recoveryContext = params.reauth === "admin" || params.reauth === "client" ? params.reauth : undefined;
  return <AuthEntry key={`${accessToken}:${recoveryContext ?? ""}`} initialInvitation={{ accessToken, returnTo }} recoveryContext={recoveryContext} />;
}
