// App est devenu une "coquille" : il ne contient plus la logique des offres,
// juste la NAVIGATION entre les écrans. Chaque écran est un composant séparé.

import { useState } from "react";

import OffersPage from "./components/OffersPage.jsx";
import StatsPage from "./components/StatsPage.jsx";

export default function App() {
  // "view" mémorise l'écran actif : "offers" ou "stats". Cliquer sur un onglet
  // change ce state, donc React réaffiche et montre l'autre composant.
  // (Pour une vraie appli multi-pages, on utiliserait React Router ; ici un
  // simple state suffit pour deux écrans.)
  const [view, setView] = useState("offers");

  return (
    <main className="container">
      <nav className="nav">
        <button
          className={view === "offers" ? "nav-link active" : "nav-link"}
          onClick={() => setView("offers")}
        >
          Offres
        </button>
        <button
          className={view === "stats" ? "nav-link active" : "nav-link"}
          onClick={() => setView("stats")}
        >
          Stats
        </button>
      </nav>

      {/* On affiche le composant correspondant à l'onglet actif. */}
      {view === "offers" ? <OffersPage /> : <StatsPage />}
    </main>
  );
}
