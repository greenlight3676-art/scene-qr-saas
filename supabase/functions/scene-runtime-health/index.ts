// Public, read-only Supabase Edge runtime liveness probe.
// Does not imply database, auth, or the Scene API is ready.
Deno.serve((request: Request) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response(null, { status: 405, headers: { Allow: "GET, HEAD", "Cache-Control": "no-store" } });
  }
  const body = JSON.stringify({ ok: true, component: "supabase-edge-runtime", api_ready: false });
  return new Response(request.method === "HEAD" ? null : body, {
    status: 200,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
});
