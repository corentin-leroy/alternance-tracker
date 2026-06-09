# Alternance Tracker

Agrégateur Python pour la recherche d'alternance en développement web/application.
Consolide les offres de plusieurs plateformes, élimine les doublons, détecte les
pièges école/CFA et garde un historique complet de tes candidatures — le tout en local.

Utilisable de deux façons : en **ligne de commande** (CLI `rich`) ou via une
**interface web locale** (API FastAPI + frontend React). Les deux partagent
exactement la même logique métier et la même base de données.

## Pourquoi ce projet ?

La recherche d'alternance en dev, c'est :
- Les mêmes offres publiées sur quatre plateformes différentes
- Des "offres d'emploi" qui sont en réalité des publicités d'écoles privées
- Aucune mémoire entre les sessions (tu revois les offres déjà vues)
- Aucun suivi des candidatures envoyées

Ce projet résout ces quatre problèmes avec un seul outil en ligne de commande.

---

## Fonctionnalités

- **4 sources d'offres** : La Bonne Alternance, France Travail, Welcome to the Jungle, HelloWork
- **Déduplication automatique** : hash exact + fuzzy matching (`rapidfuzz`, seuil 82 %) pour éliminer les doublons inter-sources
- **Détection de pièges écoles/CFA** : score de suspicion 0–1 basé sur des mots-clés et une liste noire d'entreprises
- **Historique persistant** : base SQLite locale — les offres déjà vues ne remontent plus
- **Suivi des candidatures** : enregistre la date, les notes et le statut de chaque candidature
- **CLI rich** : interface terminal avec mise en forme, navigation offre par offre et actions directes
- **Interface web locale** : API REST FastAPI + frontend React (liste filtrable, actions Postuler/Ignorer, récupération, statistiques)

---

## Prérequis

- Python 3.10+
- Node.js 18+ (uniquement pour l'interface web)
- Clés API pour les sources qui le nécessitent (voir [Configuration](#configuration))

---

## Installation

```bash
git clone <url-du-repo>
cd alternance-tracker
pip install -e .
python -m playwright install chromium
```

Pour utiliser l'**interface web**, installe en plus les dépendances optionnelles
Python et les paquets npm du frontend :

```bash
pip install -e ".[web]"          # FastAPI + uvicorn
npm --prefix frontend install    # React + Vite
```

---

## Configuration

Copie le fichier d'exemple et renseigne tes credentials :

```bash
cp .env.example .env   # Linux/macOS
copy .env.example .env  # Windows
```

```env
# France Travail — https://francetravail.io/data/api/offres-emploi
FT_CLIENT_ID=ton_client_id
FT_CLIENT_SECRET=ton_client_secret

# La Bonne Alternance — https://api.apprentissage.beta.gouv.fr
LBA_API_KEY=ta_cle_api

# Welcome to the Jungle — identifiants de ton compte wttj.com
# (le login Google ne fonctionne pas — crée un compte email/password)
WTTJ_EMAIL=ton@email.com
WTTJ_PASSWORD=ton_mot_de_passe
```

| Source | Credentials requis | Obtention |
|---|---|---|
| La Bonne Alternance | `LBA_API_KEY` | [api.apprentissage.beta.gouv.fr](https://api.apprentissage.beta.gouv.fr) |
| France Travail | `FT_CLIENT_ID` + `FT_CLIENT_SECRET` | [francetravail.io](https://francetravail.io/data/api/offres-emploi) — optionnel, activer avec `--ft` |
| Welcome to the Jungle | `WTTJ_EMAIL` + `WTTJ_PASSWORD` | Identifiants de ton compte wttj.com |
| HelloWork | aucun | Scraping HTML public |

> **WTTJ** : les résultats sont personnalisés selon ton profil. Configure ton poste souhaité,
> ta localisation et le type de contrat sur wttj.com pour des résultats pertinents.

Les paramètres de recherche géographique (Grenoble, rayon 30 km, codes ROME dev web)
sont dans `alternance_tracker/config.py`.

---

## Utilisation

### Récupérer les offres

```bash
# Sources par défaut : LBA + HelloWork + WTTJ
alternance fetch

# Inclure France Travail (nécessite FT_CLIENT_ID/FT_CLIENT_SECRET)
alternance fetch --ft
```

Exemple de sortie :
```
Récupération depuis lba…
  5 offres récupérées
Récupération depuis hellowork…
  18 offres récupérées
Récupération depuis wttj…
  4 offres récupérées

18 nouvelles offres enregistrées  (7 déjà connues, 2 doublons supprimés)
  ⚠  3 offres marquées suspectes (score ≥ 0.5)
```

---

### Passer en revue les offres

```bash
# Nouvelles offres (défaut)
alternance review

# Par statut
alternance review --status seen
alternance review --status applied
alternance review --status skipped

# Afficher aussi les offres très suspectes (score > 0.9, masquées par défaut)
alternance review --all
```

**Commandes disponibles dans la vue :**

| Touche | Action |
|---|---|
| `Entrée` | Marquer comme vue, passer à la suivante |
| `a` | Enregistrer une candidature (avec notes optionnelles) |
| `x` | Ignorer l'offre |
| `o` | Ouvrir l'URL dans le navigateur |
| `q` | Quitter |

---

### Statistiques

```bash
alternance stats
```

```
╭─ Par statut ──────────────────────╮
│ Statut                   Nombre   │
│ Nouvelles                    12   │
│ Vues                         24   │
│ Candidatures envoyées         7   │
│ Ignorées                      9   │
╰───────────────────────────────────╯
╭─ Par source ──────────────────────╮
│ Source                   Nombre   │
│ hellowork                    18   │
│ lba                           5   │
│ wttj                          4   │
│ france-travail                8   │
╰───────────────────────────────────╯

Candidatures totales : 7
```

---

## Interface web

Une interface web locale offre les mêmes fonctionnalités que la CLI dans le
navigateur. Elle se compose d'un **backend FastAPI** (qui expose la logique
métier en API REST) et d'un **frontend React**. Tout tourne en local, sans
déploiement ni authentification.

### Lancement

Deux serveurs, dans deux terminaux :

```bash
# Terminal 1 — backend (port 8000)
uvicorn alternance_tracker.api.main:app --reload

# Terminal 2 — frontend (port 5173)
npm --prefix frontend run dev
```

Puis ouvre **http://localhost:5173**. Le frontend redirige automatiquement les
appels `/api/*` vers le backend (proxy Vite).

> Documentation interactive de l'API : **http://localhost:8000/docs** — permet de
> tester chaque endpoint directement, sans frontend.

### Écrans

- **Offres** : liste filtrable (par statut, avec ou sans les offres suspectes),
  actions Postuler / Ignorer (avec annulation), et bouton de récupération.
- **Stats** : compteurs par statut et par source, et historique des candidatures.

### Endpoints

| Méthode | Endpoint | Rôle |
|---|---|---|
| `GET` | `/api/offers?status=&include_suspicious=` | Lister les offres |
| `PATCH` | `/api/offers/{id}/status` | Changer le statut (`new`/`seen`/`skipped`) |
| `POST` | `/api/offers/{id}/apply` | Enregistrer une candidature |
| `POST` | `/api/fetch` | Récupérer de nouvelles offres (lent) |
| `GET` | `/api/stats` | Statistiques agrégées |
| `GET` | `/api/applications` | Historique des candidatures |

---

## Pipeline de traitement

### Déduplication

Deux niveaux :

1. **Exacte** — chaque offre reçoit un ID `sha256(titre|entreprise|lieu)[:16]`.
   Une offre déjà connue n'est jamais réinsérée.
2. **Fuzzy** — `find_near_duplicates` détecte les quasi-doublons inter-sources
   (seuil 82 % par défaut) via `rapidfuzz.token_sort_ratio`.

### Score de suspicion

Chaque offre reçoit un score de 0.0 à 1.0. Score ≥ 0.5 = probable piège école/CFA.

| Critère | Poids |
|---|---|
| Mot-clé suspect dans le titre/description | +0.25 par mot-clé |
| Entreprise blacklistée (école recrutant pour elle-même) | +0.50 |
| Description très courte (< 200 caractères) | +0.15 |
| Absence d'URL vers l'offre originale | +0.10 |

Les offres suspectes (score ≥ 0.6) s'affichent avec un bandeau rouge `⚠ SUSPECT`.
Les pièges évidents (score > 0.9) sont masqués par défaut dans `review` —
utilise `--all` pour les voir.

---

## Structure du projet

```
alternance-tracker/
├── alternance_tracker/
│   ├── scrapers/
│   │   ├── base.py               # Classe abstraite BaseScraper
│   │   ├── labanealternance.py   # API api.apprentissage.beta.gouv.fr
│   │   ├── francetravail.py      # API OAuth2 France Travail
│   │   ├── hellowork.py          # Scraping HTML (BeautifulSoup)
│   │   └── wttj.py               # Login Playwright + API privée WTTJ
│   ├── pipeline/
│   │   ├── normalizer.py         # Génération d'ID, nettoyage HTML, parsing dates
│   │   ├── deduplicator.py       # Dédup exacte (hash) + fuzzy (rapidfuzz)
│   │   └── filter.py             # Score de suspicion 0–1
│   ├── storage/
│   │   ├── models.py             # Dataclasses Offer, Application, OfferStatus
│   │   └── db.py                 # SQLite stdlib — upsert, query, stats
│   ├── api/                      # Interface web — backend FastAPI
│   │   ├── main.py               # App FastAPI, CORS, montage des routes
│   │   ├── schemas.py            # Modèles Pydantic (contrat HTTP)
│   │   ├── deps.py               # Injection de la base de données
│   │   └── routes/               # offers, fetch, stats
│   ├── config.py                 # Mots-clés, coordonnées Grenoble, seuils
│   └── cli.py                    # Commandes fetch / review / stats (rich)
├── frontend/                     # Interface web — frontend React (Vite)
│   ├── src/
│   │   ├── App.jsx               # Navigation entre écrans
│   │   ├── api/client.js         # Appels vers l'API
│   │   └── components/           # OffersPage, OfferCard, StatsPage
│   ├── vite.config.js            # Serveur de dev + proxy /api
│   └── package.json
├── tests/
│   ├── test_deduplicator.py
│   ├── test_filter.py
│   └── test_api.py               # Tests des routes FastAPI (TestClient)
├── data/
│   └── tracker.db                # Base SQLite locale (gitignored)
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| Language | Python 3.10+ |
| Scraping HTML | BeautifulSoup 4 |
| Automatisation navigateur | Playwright (Chromium headless) |
| Fuzzy matching | rapidfuzz |
| Interface terminal | rich |
| API web | FastAPI + uvicorn |
| Frontend web | React 19 + Vite |
| Stockage | SQLite (stdlib) |
| Variables d'env | python-dotenv |

---

## Tests

```bash
pip install -e ".[dev]"   # pytest + httpx (la première fois)
pytest
```

Les tests couvrent le filtre de suspicion (`tests/test_filter.py`), le
déduplicateur (`tests/test_deduplicator.py`) et les routes de l'API web
(`tests/test_api.py`, via `TestClient` sur une base temporaire).

---

## Roadmap

- [ ] Analyse automatique des offres par LLM (adéquation profil, aide à la lettre de motivation)
- [ ] Export CSV / JSON des candidatures
- [ ] Commande `alternance apply list` pour revoir les candidatures avec relances
- [ ] Planification automatique du `fetch` (tâche cron)
- [ ] Notifications desktop quand de nouvelles offres arrivent
- [ ] Scraper Jobijoba

---

## Sécurité

Ne commite **jamais** ton fichier `.env` — il est listé dans `.gitignore`.
Le fichier `.env.example` ne doit contenir que des valeurs fictives.

L'interface web n'a pas d'authentification : elle est prévue pour un usage
**strictement local** (`localhost`). Ne l'expose pas sur un réseau public en l'état.

---

## Licence

Usage personnel. Le scraping est réalisé dans le respect des CGU des sites
concernés et avec des délais raisonnables entre les requêtes.
