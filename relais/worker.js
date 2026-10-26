// Réceptionniste Telegram de Shape Saga (Cloudflare Worker, offre gratuite).
// Telegram lui envoie chaque clic instantanément (webhook) :
//  - il répond tout de suite « ✅ Bien reçu » et remplace les 3 boutons par un bouton inactif (plus de double clic) ;
//  - il garde le clic (KV) jusqu'à ce que le robot GitHub le lise (GET /clics) puis le confirme (POST /ack).
// Un webhook actif empêche aussi tout autre programme de lire le bot (erreur 409 chez lui).
// Secrets du Worker : TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WEBHOOK_SECRET, ROBOT_KEY (posés par le workflow d'installation).

const LIBELLE = { v: "✅ Validé", r: "❌ Refusé", f: "🔁 Refaire demandé" };
const COMMANDES = { ok: "v", valider: "v", non: "r", refuser: "r" };

async function tg(env, methode, corps) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${methode}`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(corps),
  });
  return r.json().catch(() => ({}));
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json" } });
}

async function recevoir(env, maj) {
  const cq = maj.callback_query;
  const msg = maj.message;
  const chat = String((cq ? cq.message?.chat?.id : msg?.chat?.id) ?? "");
  if (chat !== String(env.TELEGRAM_CHAT_ID)) return;                       // une autre personne : ignoré

  if (cq) {
    const [act, cle] = String(cq.data || "").split(":");
    if (!LIBELLE[act] || !cle) { await tg(env, "answerCallbackQuery", { callback_query_id: cq.id }); return; }
    const deja = await env.CLICS.get(`decision:${cle}`);
    if (deja) {                                                              // 2e clic : on ne change rien
      await tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text: `Déjà enregistré : ${LIBELLE[deja]}`, show_alert: true });
      return;
    }
    await env.CLICS.put(`decision:${cle}`, act);
    await env.CLICS.put(`clic:${String(maj.update_id).padStart(12, "0")}`, JSON.stringify(maj));
    await tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text: `${LIBELLE[act]} — ${cle} bien reçu ✔️` });
    await tg(env, "editMessageReplyMarkup", {
      chat_id: cq.message.chat.id, message_id: cq.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: `${LIBELLE[act]} — enregistré, le robot s'en occupe`, callback_data: "x:fait" }]] },
    });
    return;
  }

  const texte = String(msg?.text || "").trim();
  if (!texte.startsWith("/")) return;
  const [cmd, arg] = texte.slice(1).split(/\s+/);
  const act = COMMANDES[(cmd || "").split("@")[0].toLowerCase()];
  if (act && arg) {
    const cle = /^\d+$/.test(arg) ? "EP" + arg.padStart(3, "0") : arg.toUpperCase();
    const deja = await env.CLICS.get(`decision:${cle}`);
    if (deja) { await tg(env, "sendMessage", { chat_id: chat, text: `Déjà enregistré pour ${cle} : ${LIBELLE[deja]}` }); return; }
    await env.CLICS.put(`decision:${cle}`, act);
  }
  await env.CLICS.put(`clic:${String(maj.update_id).padStart(12, "0")}`, JSON.stringify(maj));
  await tg(env, "sendMessage", { chat_id: chat, text: act && arg ? `${LIBELLE[act]} — ${arg} bien reçu ✔️` : "Bien reçu ✔️ (le robot répond à son prochain passage)" });
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === "/telegram" && req.method === "POST") {
      if (req.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) return new Response("non", { status: 403 });
      try { await recevoir(env, await req.json()); } catch (e) { console.log("erreur", e); }
      return new Response("ok");                                             // toujours 200 : Telegram ne renvoie pas en boucle
    }
    if (req.headers.get("X-Cle") !== env.ROBOT_KEY) return new Response("non", { status: 403 });
    if (url.pathname === "/clics" && req.method === "GET") {
      const liste = await env.CLICS.list({ prefix: "clic:" });
      const maj = [];
      for (const k of liste.keys) { const v = await env.CLICS.get(k.name); if (v) maj.push(JSON.parse(v)); }
      return json({ ok: true, result: maj });
    }
    if (url.pathname === "/ack" && req.method === "POST") {
      const { ids = [] } = await req.json();
      for (const id of ids) await env.CLICS.delete(`clic:${String(id).padStart(12, "0")}`);
      return json({ ok: true, supprimes: ids.length });
    }
    return new Response("Réceptionniste Shape Saga", { status: 200 });
  },
};
