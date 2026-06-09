// Point d'entrée du frontend. C'est le premier fichier JS exécuté par le
// navigateur. Son seul rôle : démarrer React et lui dire d'afficher notre
// composant <App /> dans la div #root de index.html.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  // StrictMode est une aide au développement : il signale les usages risqués.
  // Il n'a aucun effet en production.
  <StrictMode>
    <App />
  </StrictMode>,
);
