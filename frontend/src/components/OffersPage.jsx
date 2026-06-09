// Écran "Offres" : filtres, liste (via le composant OfferCard), actions
// Postuler/Ignorer avec confirmation (toast) et annulation de l'ignorance.

import { useEffect, useState } from "react";

import {
  applyToOffer,
  fetchOffers,
  getOffers,
  skipOffer,
  unskipOffer,
} from "../api/client.js";
import OfferCard from "./OfferCard.jsx";

// Options du filtre de statut. Les libellés sont en français, la valeur est
// celle attendue par l'API.
const STATUS_OPTIONS = [
  { value: "new", label: "Nouvelles" },
  { value: "seen", label: "Vues" },
  { value: "skipped", label: "Ignorées" },
];

export default function OffersPage() {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);

  // Filtres : quel statut afficher, et faut-il inclure les offres suspectes.
  const [statusFilter, setStatusFilter] = useState("new");
  const [includeSuspicious, setIncludeSuspicious] = useState(false);

  // Toast : petit message temporaire. { message, onUndo? }. onUndo est une
  // fonction optionnelle ; si présente, on affiche un bouton "Annuler".
  const [toast, setToast] = useState(null);

  function showToast(message, onUndo = null) {
    setToast({ message, onUndo });
    // Disparaît tout seul après 5 secondes.
    window.setTimeout(() => setToast(null), 5000);
  }

  // Recharge la liste selon les filtres courants. Appelée au montage, à chaque
  // changement de filtre, et après une récupération d'offres.
  async function loadOffers() {
    setLoading(true);
    try {
      const data = await getOffers(statusFilter, includeSuspicious);
      setOffers(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Les dépendances [statusFilter, includeSuspicious] : React relance cet effet
  // dès que l'un des deux change → la liste se recharge automatiquement quand
  // on touche aux filtres. C'est la grande différence avec le tableau vide [].
  useEffect(() => {
    loadOffers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, includeSuspicious]);

  function removeOffer(id) {
    setOffers((prev) => prev.filter((offer) => offer.id !== id));
  }

  async function handleApply(offer) {
    try {
      await applyToOffer(offer.id);
      removeOffer(offer.id);
      showToast("Candidature enregistrée ✓");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSkip(offer) {
    try {
      await skipOffer(offer.id);
      removeOffer(offer.id);
      // Toast avec une action d'annulation : on passe une fonction qui remettra
      // l'offre en "new".
      showToast("Offre ignorée", () => handleUndoSkip(offer));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUndoSkip(offer) {
    try {
      await unskipOffer(offer.id);
      setToast(null);
      await loadOffers(); // recharge pour que l'offre réapparaisse si pertinent
      showToast("Ignorance annulée");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFetch() {
    setFetching(true);
    setError(null);
    try {
      const result = await fetchOffers();
      await loadOffers();
      showToast(`${result.new_count} nouvelle(s) offre(s) récupérée(s)`);
    } catch (err) {
      setError(err.message);
    } finally {
      setFetching(false);
    }
  }

  return (
    <>
      <div className="header">
        <div>
          <h1>Offres d'alternance</h1>
          <p className="subtitle">{offers.length} offre(s) affichée(s)</p>
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

      {/* Barre de filtres. Modifier un filtre met à jour son state, ce qui
          déclenche le useEffect ci-dessus et recharge la liste. */}
      <div className="filters">
        <label>
          Statut :{" "}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={includeSuspicious}
            onChange={(e) => setIncludeSuspicious(e.target.checked)}
          />
          Afficher les offres suspectes
        </label>
      </div>

      {error && <p className="status error">Erreur : {error}</p>}

      {loading ? (
        <p className="status">Chargement des offres…</p>
      ) : offers.length === 0 ? (
        <p className="subtitle">Aucune offre pour ce filtre.</p>
      ) : (
        <ul className="offer-list">
          {offers.map((offer) => (
            <OfferCard
              key={offer.id}
              offer={offer}
              onApply={handleApply}
              onSkip={handleSkip}
            />
          ))}
        </ul>
      )}

      {/* Le toast, affiché seulement s'il y a un message en cours. */}
      {toast && (
        <div className="toast">
          <span>{toast.message}</span>
          {toast.onUndo && (
            <button className="toast-undo" onClick={toast.onUndo}>
              Annuler
            </button>
          )}
        </div>
      )}
    </>
  );
}
