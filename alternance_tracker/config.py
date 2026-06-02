from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "tracker.db"

SEARCH = {
    "keywords": [
        "développeur web",
        "développeur fullstack",
        "développeur frontend",
        "développeur backend",
        "développeur application",
        "web developer",
        "full stack developer",
    ],
    "location_label": "Grenoble",
    "latitude": 45.1885,
    "longitude": 5.7245,
    "insee_code": "38185",
    "department": "38",
    "radius_km": 30,
    "rome_codes": ["M1805", "M1804", "M1806"],
}

DEDUP = {
    "fuzzy_threshold": 0.82,
}

SCHOOL_TRAP_KEYWORDS = [
    "frais de scolarité",
    "frais d'inscription",
    "frais pédagogiques",
    "droits de scolarité",
    "école partenaire",
    "notre cfa",
    "notre école",
    "notre formation",
    "vous devez être inscrit",
    "trouver votre entreprise d'accueil",
    "rechercher une entreprise d'accueil",
    "financement de votre formation",
    "intégrer notre programme",
    "candidatez à notre formation",
    "postuler à notre formation",
    "prise en charge de vos frais",
]

# Entreprises connues pour poster des fausses offres d'emploi (vraiment des appels à candidature école)
SCHOOL_TRAP_COMPANIES = {
    "amos sport",
    "efap",
    "isefac",
    "iia formation",
    "m2i formation",
    "igs groupe",
    "pigier",
    "studi",
}
