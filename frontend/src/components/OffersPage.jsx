// Écran "Offres" : récupération, liste, actions Postuler/Ignorer.
// C'est exactement le code qui était dans App.jsx — on l'a juste sorti dans son
// propre composant pour que App puisse basculer entre plusieurs écrans.
// (Les chemins d'import gagnent un "../" car on est descendu d'un dossier.)

import { useEffect, useState } from "react";

import {
  applyToOffer,
  fetchOffers,
  getOffers,
  skipOffer,
} from "../api/client.js";

export default function OffersPage() {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);

  async function loadOffers() {
    const data = await getOffers("new");
    setOffers(data);
  }

  useEffect(() => {
    loadOffers()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function removeOffer(id) {
    setOffers((prev) => prev.filter((offer) => offer.id !== id));
  }

  async function handleApply(offer) {
    try {
      await applyToOffer(offer.id);
      removeOffer(offer.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSkip(offer) {
    try {
      await skipOffer(offer.id);
      removeOffer(offer.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFetch() {
    setFetching(true);
    setError(null);
    try {
      await fetchOffers();
      await loadOffers();
    } catch (err) {
      setError(err.message);
    } finally {
      setFetching(false);
    }
  }

  if (loading) {
    return <p className="status">Chargement des offres…</p>;
  }

  return (
    <>
      <div className="header">
        <div>
          <h1>Offres d'alternance</h1>
          <p className="subtitle">{offers.length} offre(s) à examiner</p>
        </div>
        <button className="btn btn-fetch" onClick={handleFetch} disabled={fetching}>
          {fetching ? (
            <>
              <span className="spinner" />
              Récupération…
            </>
          ) : (
            "Récupérer les offres"
          )}
        </button>
      </div>

      {error && <p className="status error">Erreur : {error}</p>}

      <ul className="offer-list">
        {offers.map((offer) => (
          <li key={offer.id} className="offer-card">
            <div className="offer-header">
              <h2>{offer.title}</h2>
              {offer.suspicion_score >= 0.3 && (
                <span className="badge">
                  suspect {Math.round(offer.suspicion_score * 100)}%
                </span>
              )}
            </div>
            <p className="offer-meta">
              {offer.company} · {offer.location} · {offer.source}
            </p>
            <p className="offer-desc">{offer.description.slice(0, 300)}</p>

            <div className="offer-actions">
              <button className="btn btn-apply" onClick={() => handleApply(offer)}>
                Postuler
              </button>
              <button className="btn btn-skip" onClick={() => handleSkip(offer)}>
                Ignorer
              </button>
              {offer.url && (
                <a href={offer.url} target="_blank" rel="noreferrer">
                  Voir l'offre
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
