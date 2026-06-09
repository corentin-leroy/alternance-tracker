// Carte d'une seule offre. C'est un composant "présentation" : il ne gère aucun
// état, ne fait aucun appel API. Il reçoit tout ce dont il a besoin via ses
// PROPS — les paramètres entre accolades dans la signature ci-dessous :
//   - offer    : l'objet offre à afficher
//   - onApply  : fonction à appeler quand on clique "Postuler"
//   - onSkip   : fonction à appeler quand on clique "Ignorer"
// Le parent (OffersPage) décide quoi faire ; la carte ne fait que prévenir.
// C'est le principe des props : données + comportements descendent du parent
// vers l'enfant.

export default function OfferCard({ offer, onApply, onSkip }) {
  return (
    <li className="offer-card">
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
        <button className="btn btn-apply" onClick={() => onApply(offer)}>
          Postuler
        </button>
        <button className="btn btn-skip" onClick={() => onSkip(offer)}>
          Ignorer
        </button>
        {offer.url && (
          <a href={offer.url} target="_blank" rel="noreferrer">
            Voir l'offre
          </a>
        )}
      </div>
    </li>
  );
}
