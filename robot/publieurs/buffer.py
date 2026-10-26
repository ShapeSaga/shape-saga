"""Publication via l'API GraphQL de Buffer (ouverte à l'offre gratuite depuis 2026).

Documentation : https://developers.buffer.com
- Point d'accès unique : POST https://api.buffer.com (GraphQL), en-tête « Authorization: Bearer <clé> ».
- Vidéo : pas d'envoi de fichier, uniquement une URL publique (assets: [{video: {url}}]).
- Programmation : mode customScheduled + dueAt (UTC), schedulingType automatic.
- Offre gratuite (doc Buffer, oct. 2026) : 1 clé d'API, 100 requêtes / 24 h, 3 000 / 30 jours.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..reseau import ErreurHTTP, requete
from .base import ErreurPublication, Publication, Publieur, Resultat

log = logging.getLogger(__name__)

URL = "https://api.buffer.com"

Q_ORGANISATIONS = "query { account { organizations { id name } } }"
Q_CANAUX = """query Canaux($org: OrganizationId!) {
  channels(input: {organizationId: $org}) { id name displayName service isQueuePaused }
}"""
Q_FILE = """query File($org: OrganizationId!, $canal: ChannelId!) {
  posts(first: 50, input: {organizationId: $org, filter: {status: [scheduled], channelIds: [$canal]}}) {
    edges { node { id dueAt } }
  }
}"""
Q_STATS = """query Stats($org: OrganizationId!, $canal: ChannelId!) {
  posts(first: 30, input: {organizationId: $org, filter: {status: [sent], channelIds: [$canal]}}) {
    edges { node { id text dueAt metrics { name value } } }
  }
}"""
M_CREER = """mutation Creer($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess { post { id dueAt } }
    ... on MutationError { message }
  }
}"""


class PublieurBuffer(Publieur):
    nom = "buffer"
    programmation_distante = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reglages = self.conf["publication"]["buffer"]
        self._org: str | None = self.reglages.get("organisation_id") or None
        self._canaux: dict[str, dict] | None = None

    @property
    def limite_file(self) -> int | None:
        return int(self.conf["publication"].get("limite_file_par_canal", 10))

    # ------------------------------------------------------------------ GraphQL
    def gql(self, requete_gql: str, variables: dict | None = None, tentatives: int = 3) -> dict:
        if not self.secrets.buffer:
            raise ErreurPublication("BUFFER_API_KEY absente", temporaire=False)
        try:
            rep = requete(self.session, "POST", URL, json={"query": requete_gql, "variables": variables or {}},
                          headers={"Authorization": f"Bearer {self.secrets.buffer}"},
                          tentatives=tentatives, etiquette="Buffer")
        except ErreurHTTP as exc:
            raise ErreurPublication(f"Buffer : {exc}", temporaire=exc.statut not in (400, 401, 403)) from exc
        corps = rep.json()
        if corps.get("errors"):
            messages = "; ".join(e.get("message", "?") for e in corps["errors"])
            raise ErreurPublication(f"Buffer GraphQL : {messages}", temporaire=False)
        return corps.get("data") or {}

    def organisation(self) -> str:
        if not self._org:
            orgs = self.gql(Q_ORGANISATIONS)["account"]["organizations"]
            if not orgs:
                raise ErreurPublication("aucune organisation Buffer", temporaire=False)
            self._org = orgs[0]["id"]
        return self._org

    def canaux(self) -> dict[str, dict]:
        """Canaux par plateforme (« service » Buffer en minuscules)."""
        if self._canaux is None:
            liste = self.gql(Q_CANAUX, {"org": self.organisation()})["channels"]
            imposes = {p: c for p, c in (self.reglages.get("canaux") or {}).items() if c}
            self._canaux = {}
            for canal in liste:
                service = str(canal.get("service", "")).lower()
                if service in imposes and canal["id"] != imposes[service]:
                    continue
                self._canaux.setdefault(service, canal)
        return self._canaux

    def canal(self, plateforme: str) -> dict:
        canal = self.canaux().get(plateforme)
        if not canal:
            raise ErreurPublication(f"aucun canal {plateforme} connecté dans Buffer", temporaire=False)
        return canal

    # ------------------------------------------------------------------ interface
    def tester_connexion(self) -> str:
        canaux = self.canaux()
        voulues = [p for p in self.conf["publication"]["plateformes"]
                   if self.conf["publication"]["publieurs"].get(p) == "buffer"]
        manquants = [p for p in voulues if p not in canaux]
        resume = ", ".join(f"{s} ({c.get('displayName') or c.get('name')})" for s, c in canaux.items())
        if manquants:
            raise ErreurPublication(f"canaux absents dans Buffer : {', '.join(manquants)} (trouvés : {resume or 'aucun'})",
                                    temporaire=False)
        en_pause = [s for s, c in canaux.items() if c.get("isQueuePaused") and s in voulues]
        if en_pause:
            resume += f" — ATTENTION file en pause : {', '.join(en_pause)}"
        return f"Buffer OK : {resume}"

    def places_disponibles(self, plateforme: str) -> int | None:
        canal = self.canal(plateforme)
        data = self.gql(Q_FILE, {"org": self.organisation(), "canal": canal["id"]})
        occupes = len(data["posts"]["edges"])
        return max(0, (self.limite_file or 10) - occupes)

    def metadonnees(self, pub: Publication) -> dict:
        """Uniquement des champs qui existent dans le schéma Buffer (vérifié sur developers.buffer.com).

        YouTube : title, privacy, categoryId, license, notifySubscribers, embeddable, madeForKids.
        Instagram : type, firstComment, geolocation, shouldShareToFeed, stickerFields.
        TikTok : title (photos), isAiGenerated (vidéos).
        Il n'existe PAS de champ « IA » pour YouTube/Instagram dans l'API : `aiAssisted` (niveau post) suffit.
        """
        if pub.plateforme == "youtube":
            return {"youtube": {
                "title": (pub.titre or pub.texte.splitlines()[0])[:100],
                "categoryId": str(self.reglages.get("youtube_categorie", "24")),
                "privacy": "public",
                "madeForKids": False,
                "notifySubscribers": True,
                "embeddable": True,
            }}
        if pub.plateforme == "instagram":
            ig = {"type": "reel", "shouldShareToFeed": True}
            if pub.premier_commentaire:
                ig["firstComment"] = pub.premier_commentaire[:2200]
            return {"instagram": ig}
        if pub.plateforme == "tiktok":
            return {"tiktok": {"isAiGenerated": True}} if pub.contenu_ia else {}
        return {}

    def _programmer(self, pub: Publication) -> Resultat:
        if not pub.video_url:
            raise ErreurPublication("adresse publique de la vidéo manquante", temporaire=False)
        canal = self.canal(pub.plateforme)
        au_plus_tot = datetime.now(timezone.utc) + timedelta(minutes=5)
        date = max(pub.date, au_plus_tot)
        video: dict = {"url": pub.video_url}
        if pub.plateforme in ("tiktok", "instagram"):
            video["metadata"] = {"thumbnailOffset": int(pub.miniature_ms)}
        entree = {
            "channelId": canal["id"],
            "text": pub.texte,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": self.date_utc(date),
            "assets": [{"video": video}],
            "metadata": self.metadonnees(pub),
            "aiAssisted": pub.contenu_ia,
        }
        if pub.brouillon:                       # test : rien ne sera publié
            entree.pop("dueAt"); entree["mode"] = "addToQueue"; entree["saveToDraft"] = True
        res = self.gql(M_CREER, {"input": entree}, tentatives=1)["createPost"]
        if res.get("__typename") == "PostActionSuccess" or res.get("post"):
            post = res["post"]
            quand = "BROUILLON (rien publié)" if pub.brouillon else f"programmé pour {entree['dueAt']}"
            log.info("Buffer : %s %s sur %s (post %s)", pub.episode_id, quand, pub.plateforme, post["id"])
            return Resultat(id_distant=post["id"], message=quand)
        raise ErreurPublication(f"Buffer a refusé le post : {res.get('message', res)}", temporaire=False)

    def statistiques(self, depuis: datetime) -> dict | None:
        resultat: dict = {}
        for service, canal in self.canaux().items():
            try:
                edges = self.gql(Q_STATS, {"org": self.organisation(), "canal": canal["id"]})["posts"]["edges"]
            except ErreurPublication as exc:
                log.warning("Statistiques Buffer %s indisponibles : %s", service, exc)
                continue
            posts = []
            for e in edges:
                n = e["node"]
                due = n.get("dueAt")
                if due and datetime.fromisoformat(due.replace("Z", "+00:00")) < depuis:
                    continue
                mesures = {m["name"]: m.get("value") for m in (n.get("metrics") or []) if m.get("name")}
                posts.append({"id": n["id"], "texte": (n.get("text") or "")[:80], "date": due, "mesures": mesures})
            resultat[service] = {"posts": posts}
        return resultat
