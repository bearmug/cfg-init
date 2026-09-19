// Local model gate: low-power and saturation guard for any OpenAI-compatible
// upstream server. Listens on 127.0.0.1:8090 and forwards to 127.0.0.1:8080
// by default; override MODEL_GATE_UPSTREAM, MODEL_GATE_PORT, and
// MODEL_GATE_LIMIT for another backend/model. The Bonsai 2 values are merely
// the tested example/default, not part of the gate policy.
// Saturated or LPM -> immediate HTTP 503, no queue. The 503 shape matches
// harness transient classifiers so the caller can spill over to its fallback.
// A dead /slots probe fails open; a dead upstream returns 503.
// Observability: GET /health and GET /gate-status.
// NOTE: idleTimeout 255 = Bun max; long non-streaming calls remain supported.
const UPSTREAM = Bun.env.MODEL_GATE_UPSTREAM ?? Bun.env.BONSAI_UPSTREAM ?? "http://127.0.0.1:8080";
const PORT = Number(Bun.env.MODEL_GATE_PORT ?? Bun.env.BONSAI_GATE_PORT ?? 8090);
const LIMIT = Number(Bun.env.MODEL_GATE_LIMIT ?? Bun.env.BONSAI_GATE_BUSY_LIMIT ?? 2);
const SLOT_TIMEOUT_MS = 2500;

const startedAt = Date.now();
let active = 0;
let reqSeq = 0;
const counters = { fwd: 0, gatedLpm: 0, gatedBusy: 0, upstreamErr: 0 };

let lpmCache = { at: 0, val: 0 };
function lowPowerMode() {
	const now = Date.now();
	if (now - lpmCache.at < 2000) return lpmCache.val;
	let val = 0;
	try {
		const p = Bun.spawnSync(["pmset", "-g"]);
		const out = p.stdout ? Buffer.from(p.stdout).toString("utf8") : "";
		const m = /^\s*lowpowermode\s+(\d)/m.exec(out);
		if (m) val = Number(m[1]);
	} catch {
		/* fail open */
	}
	lpmCache = { at: now, val };
	return val;
}

async function upstreamSlots() {
	const ctl = new AbortController();
	const t = setTimeout(() => ctl.abort(), SLOT_TIMEOUT_MS);
	try {
		const r = await fetch(`${UPSTREAM}/slots`, { signal: ctl.signal });
		if (!r.ok) return { busy: 0, total: 4, ok: false };
		const slots = await r.json();
		if (!Array.isArray(slots)) return { busy: 0, total: 4, ok: false };
		return { busy: slots.filter(s => s && s.is_processing).length, total: slots.length, ok: true };
	} finally {
		clearTimeout(t);
	}
}

const ts = () => new Date().toISOString();

const gate = msg =>
	Response.json(
		{ error: { message: `${msg}: overloaded, no capacity, retry later`, type: "server_error", code: 503 } },
		{ status: 503, headers: { "Retry-After": "5" } },
	);

function forward(req, u) {
	const fwd = new URL(u.pathname + u.search, UPSTREAM);
	const headers = new Headers(req.headers);
	headers.delete("host");
	headers.delete("content-length");
	return fetch(fwd, {
		method: req.method,
		headers,
		body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body,
		// @ts-ignore Bun half-duplex streaming
		duplex: "half",
	});
}

const server = Bun.serve({
	port: PORT,
	hostname: "127.0.0.1",
	idleTimeout: 255,
	async fetch(req) {
		const u = new URL(req.url);
		if (req.method === "GET" && u.pathname === "/health") {
			return Response.json({ status: "ok", service: "model-gate" });
		}
		if (req.method === "GET" && u.pathname === "/gate-status") {
			let slots = { busy: -1, total: -1, ok: false };
			try {
				slots = await upstreamSlots();
			} catch {
				/* report probe failure, still 200 */
			}
			return Response.json({
				lpm: lowPowerMode(),
				upstream_busy: slots.busy,
				upstream_total: slots.total,
				upstream_ok: slots.ok,
				active,
				limit: LIMIT,
				uptime_s: Math.round((Date.now() - startedAt) / 1000),
				counters,
			});
		}
		const chatPath = u.pathname === "/v1/chat/completions" || u.pathname === "/v1/completions";
	if (req.method === "POST" && chatPath) {
		const id = ++reqSeq;
		if (lowPowerMode() === 1) {
			counters.gatedLpm++;
			console.log(`[${ts()}] #${id} GATE lpm=1 -> 503`);
			return gate("Model gate: low power mode active");
		}
		let busy = 0,
			total = 4,
			ok = false;
		try {
			({ busy, total, ok } = await upstreamSlots());
		} catch {
			/* probe failed -> fail open on the upstream count */
		}
		if (active >= LIMIT || (ok && busy >= LIMIT)) {
			counters.gatedBusy++;
			console.log(`[${ts()}] #${id} GATE busy=${busy}/${total} active=${active} limit=${LIMIT} -> 503`);
			return gate(`Model gate: local overloaded (${busy}/${total} slots busy, ${active} forwarding)`);
		}
		counters.fwd++;
		active++;
		console.log(`[${ts()}] #${id} FWD active=${active} upstream=${busy}/${total}`);
		try {
			return await forward(req, u);
		} catch (e) {
			counters.upstreamErr++;
			console.log(`[${ts()}] #${id} UPSTREAM-ERR ${String(e).slice(0, 160)} -> 503`);
			return gate(`Model gate: upstream unavailable (${String(e).slice(0, 80)})`);
		} finally {
			active--;
		}
	}
		try {
			return await forward(req, u);
		} catch (e) {
			counters.upstreamErr++;
			return gate(`Model gate: upstream unavailable (${String(e).slice(0, 80)})`);
		}
	},
});
console.log(`model-gate listening on http://127.0.0.1:${PORT} -> ${UPSTREAM} (limit=${LIMIT}, immediate-503, no queue)`);
