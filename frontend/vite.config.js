import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configuration de Vite (le serveur de dev + l'outil de build).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy : toute requête du front vers "/api/..." est transférée au backend
    // FastAPI sur le port 8000. Avantage : depuis le code React on écrit juste
    // fetch("/api/offers") sans se soucier du port, et ça évite les erreurs
    // CORS du navigateur (tout passe par la même origine localhost:5173).
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
