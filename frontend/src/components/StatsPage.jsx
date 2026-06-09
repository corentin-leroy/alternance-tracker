// Écran "Stats" : compteurs (GET /api/stats) + historique des candidatures
// (GET /api/applications). Lecture seule — aucune action, aucune mutation.

import { useEffect, useState } from "react";

import { getApplications, getStats } from "../api/client.js";

// Libellés lisibles pour les statuts techniques (comme dans la CLI).
const STATUS_LABELS = {
  new: "Nouvelles",
  seen: "Vues",
  applied: "Candidatures envoyées",
  skipped: "Ignorées",
  rejected: "Refusées",
};

export default function StatsPage() {
  const [stats, setStats] = useState(null);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Promise.all lance les DEUX requêtes en parallèle et attend que les deux
    // soient terminées. Plus rapide que de les enchaîner l'une après l'autre.
    // Le résultat arrive dans le même ordre que les promesses passées.
    Promise.all([getStats(), getApplications()])
      .then(([statsData, appsData]) => {
        setStats(statsData);
        setApplications(appsData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="status">Chargement des statistiques…</p>;
  }
  if (error) {
    return <p className="status error">Erreur : {error}</p>;
  }

  // Object.entries transforme un objet { new: 12, seen: 3 } en une liste de
  // paires [ ["new", 12], ["seen", 3] ] sur laquelle on peut faire .map().
  return (
    <>
      <h1>Statistiques</h1>

      <h2 className="stats-title">Par statut</h2>
      <table className="stats-table">
        <tbody>
          {Object.entries(stats.by_status).map(([status, count]) => (
            <tr key={status}>
              <td>{STATUS_LABELS[status] || status}</td>
              <td className="num">{count}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="stats-title">Par source</h2>
      <table className="stats-table">
        <tbody>
          {Object.entries(stats.by_source).map(([source, count]) => (
            <tr key={source}>
              <td>{source}</td>
              <td className="num">{count}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="stats-total">
        Candidatures totales : <strong>{stats.total_applications}</strong>
      </p>

      <h2 className="stats-title">Historique des candidatures</h2>
      {applications.length === 0 ? (
        <p className="subtitle">Aucune candidature enregistrée pour l'instant.</p>
      ) : (
        <table className="stats-table">
          <tbody>
            {applications.map((app) => (
              <tr key={app.id}>
                <td>{new Date(app.applied_at).toLocaleDateString("fr-FR")}</td>
                <td>
                  {app.offer_title || <span className="muted">offre supprimée</span>}
                  {app.offer_company && (
                    <span className="muted"> · {app.offer_company}</span>
                  )}
                </td>
                <td>{app.notes || <span className="muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
