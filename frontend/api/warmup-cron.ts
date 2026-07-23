/**
 * Vercel Serverless Function: cron warmup ping.
 *
 * Vercel Cron invokes this endpoint every 5 minutes (see vercel.json `crons`).
 * It pings the Render backend's /api/warmup endpoint to prevent the free-tier
 * container from sleeping (Render sleeps after 15 min of inactivity).
 *
 * IMPORTANT: This runs on Vercel's edge — it does NOT count against the
 * user's Render request quota in any meaningful way (each ping is < 1KB).
 *
 * Env vars (set in Vercel project settings):
 *   BACKEND_URL  — e.g. https://decision-lens-apac.onrender.com
 *   CRON_SECRET  — optional shared secret; if set, Vercel sends it as
 *                  `Authorization: Bearer <CRON_SECRET>` header. We don't
 *                  require it here since the endpoint is read-only and
 *                  harmless, but you can add it for tighter auth.
 */
export default async function handler(req, res) {
  const backendUrl = process.env.BACKEND_URL || 'https://decision-lens-apac.onrender.com'
  const startedAt = Date.now()

  try {
    // 5s timeout — if Render is asleep, the first ping might take 30-45s
    // to wake up. We don't want Vercel to retry (it would compound), so
    // we accept the timeout and let the NEXT cron run find the container
    // already warm.
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 10000)

    const r = await fetch(`${backendUrl}/api/warmup`, {
      method: 'GET',
      signal: controller.signal,
      headers: { 'User-Agent': 'vercel-cron-warmup/1.0' },
    })
    clearTimeout(timeout)

    const elapsedMs = Date.now() - startedAt
    const body = await r.text()

    return res.status(200).json({
      ok: true,
      backend_status: r.status,
      elapsed_ms: elapsedMs,
      backend_url: backendUrl,
      backend_response: body.slice(0, 200),
      timestamp: new Date().toISOString(),
    })
  } catch (err) {
    const elapsedMs = Date.now() - startedAt
    return res.status(200).json({
      ok: false,
      error: String(err.message || err),
      elapsed_ms: elapsedMs,
      backend_url: backendUrl,
      timestamp: new Date().toISOString(),
      note: 'Backend likely sleeping — next cron run (5 min) will find it warm.',
    })
  }
}
