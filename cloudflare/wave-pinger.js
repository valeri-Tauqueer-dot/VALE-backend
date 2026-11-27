/**
 * VALE Cloudflare launcher - batch 15 of the plan (optional).
 *
 * This is NOT a second copy of the wave system - wave_runner.py and
 * wave.yml (GitHub Actions) already do the real checking work, for
 * free, every 6 hours. What THIS file adds, on Cloudflare's own free
 * plan, is simply an extra, independent trigger: every 15 minutes, it
 * asks your Render app to run its self-test, which also has the side
 * effect of waking Render up if the free instance had gone to sleep
 * from no visitors - so a real person opening the app is less likely
 * to hit that first-request delay.
 *
 * Free Cloudflare Workers limits (as found): 100,000 requests/day,
 * 10ms of CPU time per request - this file barely uses either, since
 * all it does is start one outside fetch and return.
 *
 * Setup (free, no card needed):
 *   1. workers.cloudflare.com -> create a Worker -> paste this file in.
 *   2. In the Worker's settings, add a Cron Trigger: every 15 minutes
 *      (or whatever you like - wrangler.toml alongside this file shows
 *      the same schedule, if you deploy with the CLI instead).
 *   3. That's it - no database, no secrets needed for this file itself.
 */

const TARGET_URL = "https://vale-backend-ye4r.onrender.com/self-test";

export default {
  async scheduled(event, env, ctx) {
    try {
      const response = await fetch(TARGET_URL, {
        headers: { "User-Agent": "VALE-cloudflare-pinger/1.0" },
      });
      console.log("VALE PINGER: got status", response.status);
    } catch (error) {
      // Never let a failed ping break anything else - just log it.
      console.log("VALE PINGER: fetch failed:", error.message);
    }
  },

  // Lets you also trigger it by hand by visiting the Worker's own URL.
  async fetch(request, env, ctx) {
    await this.scheduled(null, env, ctx);
    return new Response("VALE pinger ran - check Render's logs or /self-test for results.");
  },
};
