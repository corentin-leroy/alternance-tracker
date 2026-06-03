"""Wizard interactif pour configurer le .env au premier lancement."""

from pathlib import Path
from typing import Optional

import requests
from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

console = Console(legacy_windows=False)
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_existing() -> dict[str, str]:
    return dict(dotenv_values(ENV_PATH)) if ENV_PATH.exists() else {}


def _geocode(city: str) -> Optional[dict]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{city}, France", "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": "alternance-tracker-init/1.0"},
            timeout=10,
        )
        results = resp.json()
        if not results:
            return None
        r = results[0]
        postcode = r.get("address", {}).get("postcode", "")
        # Gestion des DOM (971, 972…) et codes normaux (38, 75…)
        dept = ""
        if postcode and len(postcode) >= 2:
            dept = postcode[:3] if postcode[:2] in ("97", "98") else postcode[:2]
        return {"lat": float(r["lat"]), "lon": float(r["lon"]), "department": dept}
    except Exception:
        return None


def _validate_lba(api_key: str) -> tuple[bool, str]:
    try:
        resp = requests.get(
            "https://api.apprentissage.beta.gouv.fr/api/job/v1/search",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"latitude": 45.1885, "longitude": 5.7245, "radius": 10, "romes": "M1805"},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, ""
        if resp.status_code == 401:
            return False, "Clé invalide (401 Unauthorized)"
        return False, f"Erreur HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Connexion impossible : {e}"


def _validate_ft(client_id: str, client_secret: str) -> tuple[bool, str]:
    try:
        resp = requests.post(
            "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True, ""
        if resp.status_code in (400, 401):
            return False, "Identifiants invalides (vérifiez client_id / client_secret)"
        return False, f"Erreur HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Connexion impossible : {e}"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _section_search(existing: dict) -> dict:
    console.print(Rule("[bold]1 / 4 — Paramètres de recherche[/bold]"))
    console.print("[dim]Définissent la zone géographique où chercher les offres.[/dim]\n")

    city = Prompt.ask(
        "Ville de recherche",
        default=existing.get("SEARCH_CITY", "Grenoble"),
    )

    console.print(f"  [cyan]Géolocalisation de « {city} »…[/cyan] ", end="")
    geo = _geocode(city)
    if geo:
        console.print(f"[green]✓[/green] lat={geo['lat']:.4f}  lon={geo['lon']:.4f}")
    else:
        console.print("[yellow]introuvable, saisie manuelle requise[/yellow]")

    default_lat = f"{geo['lat']:.6f}" if geo else existing.get("SEARCH_LATITUDE", "45.1885")
    default_lon = f"{geo['lon']:.6f}" if geo else existing.get("SEARCH_LONGITUDE", "5.7245")
    default_dept = geo["department"] if geo else existing.get("SEARCH_DEPARTMENT", "38")

    lat = Prompt.ask("  Latitude", default=default_lat)
    lon = Prompt.ask("  Longitude", default=default_lon)
    dept = Prompt.ask("  Code département (ex: 38, 75, 69)", default=default_dept)
    radius = Prompt.ask("  Rayon de recherche (km)", default=existing.get("SEARCH_RADIUS_KM", "30"))

    return {
        "SEARCH_CITY": city,
        "SEARCH_LATITUDE": lat,
        "SEARCH_LONGITUDE": lon,
        "SEARCH_DEPARTMENT": dept,
        "SEARCH_RADIUS_KM": radius,
    }


def _section_lba(existing: dict) -> dict:
    console.print(Rule("[bold]2 / 4 — La Bonne Alternance[/bold]"))
    console.print(
        "[green bold]Recommandée[/green bold] — Source gouvernementale, gratuite, sans Playwright.\n"
        "Inscription : https://api.apprentissage.beta.gouv.fr\n"
        "[dim](créer un compte, puis Applications > Générer une clé)[/dim]\n"
    )

    current = existing.get("LBA_API_KEY", "")
    if current:
        console.print(f"[dim]Clé actuelle : {current[:10]}…[/dim]")
        if not Confirm.ask("  Modifier ?", default=False):
            return {"LBA_API_KEY": current}

    api_key = Prompt.ask("  LBA_API_KEY [dim](Entrée pour passer)[/dim]", default="").strip()
    if not api_key:
        console.print("[yellow]  Source LBA désactivée.[/yellow]")
        return {"LBA_API_KEY": ""}

    console.print("  [cyan]Test de la clé…[/cyan] ", end="")
    ok, err = _validate_lba(api_key)
    if ok:
        console.print("[green]✓ Clé valide[/green]")
    else:
        console.print(f"[red]✗ {err}[/red]")
        if not Confirm.ask("  Conserver quand même ?", default=False):
            return {"LBA_API_KEY": ""}

    return {"LBA_API_KEY": api_key}


def _section_ft(existing: dict) -> dict:
    console.print(Rule("[bold]3 / 4 — France Travail[/bold]"))
    console.print(
        "[dim]Optionnel[/dim] — Offres France Travail via API officielle.\n"
        "Inscription (gratuite) : https://francetravail.io/data/api/offres-emploi\n"
        "[dim](créer une application, scope « Offres d'emploi »)\n"
        "Activé via [bold]alternance fetch --ft[/bold][/dim]\n"
    )

    has_existing = existing.get("FT_CLIENT_ID") and existing.get("FT_CLIENT_SECRET")
    if has_existing:
        console.print(f"[dim]Client ID actuel : {existing['FT_CLIENT_ID'][:10]}…[/dim]")
        if not Confirm.ask("  Modifier ?", default=False):
            return {"FT_CLIENT_ID": existing["FT_CLIENT_ID"], "FT_CLIENT_SECRET": existing["FT_CLIENT_SECRET"]}

    if not Confirm.ask("  Configurer France Travail ?", default=bool(has_existing)):
        return {"FT_CLIENT_ID": "", "FT_CLIENT_SECRET": ""}

    client_id = Prompt.ask("  FT_CLIENT_ID").strip()
    client_secret = Prompt.ask("  FT_CLIENT_SECRET", password=True).strip()

    console.print("  [cyan]Test des identifiants…[/cyan] ", end="")
    ok, err = _validate_ft(client_id, client_secret)
    if ok:
        console.print("[green]✓ Identifiants valides[/green]")
    else:
        console.print(f"[red]✗ {err}[/red]")
        if not Confirm.ask("  Conserver quand même ?", default=False):
            return {"FT_CLIENT_ID": "", "FT_CLIENT_SECRET": ""}

    return {"FT_CLIENT_ID": client_id, "FT_CLIENT_SECRET": client_secret}


def _section_wttj(existing: dict) -> dict:
    console.print(Rule("[bold]4 / 4 — Welcome to the Jungle[/bold]"))
    console.print(
        "[dim]Optionnel[/dim] — Offres personnalisées depuis votre profil WTTJ.\n"
        "Compte requis : https://www.welcometothejungle.com\n"
        "[dim]Requiert Playwright (pip install playwright && py -m playwright install chromium).\n"
        "Les résultats dépendent de votre profil WTTJ (poste, lieu, type de contrat).[/dim]\n"
    )

    has_existing = existing.get("WTTJ_EMAIL") and existing.get("WTTJ_PASSWORD")
    if has_existing:
        console.print(f"[dim]Compte actuel : {existing['WTTJ_EMAIL']}[/dim]")
        if not Confirm.ask("  Modifier ?", default=False):
            return {"WTTJ_EMAIL": existing["WTTJ_EMAIL"], "WTTJ_PASSWORD": existing["WTTJ_PASSWORD"]}

    if not Confirm.ask("  Configurer WTTJ ?", default=bool(has_existing)):
        return {"WTTJ_EMAIL": "", "WTTJ_PASSWORD": ""}

    email = Prompt.ask("  WTTJ_EMAIL").strip()
    password = Prompt.ask("  WTTJ_PASSWORD", password=True).strip()
    console.print("[dim]  (Validation impossible sans Playwright — testée au prochain fetch)[/dim]")

    return {"WTTJ_EMAIL": email, "WTTJ_PASSWORD": password}


# ---------------------------------------------------------------------------
# Écriture du .env
# ---------------------------------------------------------------------------

def _write_env(config: dict):
    lines = [
        "# Paramètres de recherche",
        f"SEARCH_CITY={config.get('SEARCH_CITY', 'Grenoble')}",
        f"SEARCH_LATITUDE={config.get('SEARCH_LATITUDE', '45.1885')}",
        f"SEARCH_LONGITUDE={config.get('SEARCH_LONGITUDE', '5.7245')}",
        f"SEARCH_DEPARTMENT={config.get('SEARCH_DEPARTMENT', '38')}",
        f"SEARCH_RADIUS_KM={config.get('SEARCH_RADIUS_KM', '30')}",
        "",
        "# La Bonne Alternance (recommandée) — https://api.apprentissage.beta.gouv.fr",
        f"LBA_API_KEY={config.get('LBA_API_KEY', '')}",
        "",
        "# France Travail (optionnel) — https://francetravail.io/data/api/offres-emploi",
        f"FT_CLIENT_ID={config.get('FT_CLIENT_ID', '')}",
        f"FT_CLIENT_SECRET={config.get('FT_CLIENT_SECRET', '')}",
        "",
        "# Welcome to the Jungle (optionnel) — nécessite Playwright",
        f"WTTJ_EMAIL={config.get('WTTJ_EMAIL', '')}",
        f"WTTJ_PASSWORD={config.get('WTTJ_PASSWORD', '')}",
    ]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def run():
    console.print(Panel(
        "[bold cyan]alternance init[/bold cyan]\n\n"
        "Configuration interactive du tracker.\n"
        "Appuyez sur [bold]Entrée[/bold] pour accepter la valeur entre crochets.",
        title="Bienvenue",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    existing = _load_existing()
    if ENV_PATH.exists():
        console.print(f"[yellow]Un .env existe déjà ({ENV_PATH}).[/yellow]")
        console.print("[dim]Les valeurs actuelles sont proposées par défaut.\n[/dim]")

    config: dict[str, str] = {}
    config.update(_section_search(existing))
    console.print()
    config.update(_section_lba(existing))
    console.print()
    config.update(_section_ft(existing))
    console.print()
    config.update(_section_wttj(existing))
    console.print()

    _write_env(config)

    console.print(Rule())
    console.print(f"[bold green]✓ .env écrit dans {ENV_PATH}[/bold green]\n")

    active = ["[cyan]hellowork[/cyan] [dim](aucune clé)[/dim]"]
    if config.get("LBA_API_KEY"):
        active.append("[cyan]lba[/cyan]")
    if config.get("FT_CLIENT_ID") and config.get("FT_CLIENT_SECRET"):
        active.append("[cyan]france-travail[/cyan] [dim](--ft)[/dim]")
    if config.get("WTTJ_EMAIL") and config.get("WTTJ_PASSWORD"):
        active.append("[cyan]wttj[/cyan]")

    console.print("Sources configurées : " + "  ·  ".join(active))
    console.print("\nLancez [bold]alternance fetch[/bold] pour récupérer vos premières offres.")
