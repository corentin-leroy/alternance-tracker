// Toutes les communications avec le backend FastAPI passent par ce fichier.
// Regrouper les appels réseau ici (plutôt que de les éparpiller dans les
// composants) rend le code plus facile à suivre et à modifier.

// Grâce au proxy défini dans vite.config.js, "/api" pointe vers le backend
// sur le port 8000 — on n'a pas à écrire l'URL complète.

export async function getOffers(status = "new", includeSuspicious = false) {
  const params = new URLSearchParams({
    status,
    include_suspicious: includeSuspicious,
  });
  const response = await fetch(`/api/offers?${params}`);
  if (!response.ok) {
    throw new Error(`Erreur API (${response.status})`);
  }
  return response.json();
}

// Récupère les statistiques → GET /api/stats
// Renvoie { by_status, by_source, total_applications }.
export async function getStats() {
  const response = await fetch("/api/stats");
  if (!response.ok) {
    throw new Error(`Erreur API (${response.status})`);
  }
  return response.json();
}

// Récupère l'historique des candidatures → GET /api/applications
// Renvoie une liste de { id, offer_id, applied_at, notes, response, follow_up_at }.
export async function getApplications() {
  const response = await fetch("/api/applications");
  if (!response.ok) {
    throw new Error(`Erreur API (${response.status})`);
  }
  return response.json();
}

// Petit utilitaire interne : envoie une requête avec un corps JSON.
// GET n'a pas de corps, mais POST/PATCH si — il faut préciser la méthode,
// l'en-tête Content-Type, et sérialiser l'objet JS en texte JSON.
async function sendJson(url, method, body) {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Erreur API (${response.status})`);
  }
  return response.json();
}

// Postuler à une offre → POST /api/offers/{id}/apply
// Le backend enregistre la candidature et passe l'offre au statut "applied".
export function applyToOffer(id, notes = "") {
  return sendJson(`/api/offers/${id}/apply`, "POST", { notes });
}

// Change le statut d'une offre → PATCH /api/offers/{id}/status
// Statuts acceptés par le backend : "new", "seen", "skipped".
export function updateOfferStatus(id, status) {
  return sendJson(`/api/offers/${id}/status`, "PATCH", { status });
}

// Raccourcis lisibles construits sur la fonction générique ci-dessus.
export function skipOffer(id) {
  return updateOfferStatus(id, "skipped");
}

export function unskipOffer(id) {
  return updateOfferStatus(id, "new");
}

// Lancer une récupération d'offres → POST /api/fetch
// Côté backend, ça déclenche les scrapers (lent). Renvoie un résumé chiffré
// (combien de nouvelles offres, doublons, etc.).
export function fetchOffers() {
  return sendJson("/api/fetch", "POST", {});
}
