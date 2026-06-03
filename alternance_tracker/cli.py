import argparse
import os
import sys
import webbrowser

import requests
from datetime import datetime

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

# Force UTF-8 sur Windows (les descriptions d'offres contiennent des emojis et
# caractères hors cp1252 que le renderer legacy Windows ne peut pas encoder)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .config import DB_PATH
from .init_wizard import run as run_init_wizard
from .pipeline.deduplicator import deduplicate
from .pipeline.filter import apply_filter
from .scrapers.francetravail import FranceTravailScraper
from .scrapers.hellowork import HelloworkScraper
from .scrapers.labanealternance import LaBonneAlternanceScraper
from .scrapers.wttj import WttjScraper
from .storage.db import Database
from .storage.models import Application, Offer, OfferStatus

console = Console(legacy_windows=False)


def _get_db() -> Database:
    return Database(DB_PATH)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def cmd_fetch(args):
    db = _get_db()
    scrapers = [LaBonneAlternanceScraper(), HelloworkScraper(), WttjScraper()]
    if args.ft or (os.getenv("FT_CLIENT_ID") and os.getenv("FT_CLIENT_SECRET")):
        scrapers.append(FranceTravailScraper())

    all_offers: list[Offer] = []
    for scraper in scrapers:
        console.print(f"[cyan]Récupération depuis {scraper.name}…[/cyan]")
        try:
            offers = scraper.fetch()
            console.print(f"  [green]{len(offers)} offres récupérées[/green]")
            all_offers.extend(offers)
        except requests.exceptions.RequestException as e:
            console.print(f"  [red]Erreur réseau : {e}[/red]")
        except EnvironmentError as e:
            console.print(f"  [yellow]Configuration manquante : {e}[/yellow]")
        except Exception as e:
            console.print(f"  [red]Erreur : {e}[/red]")

    if not all_offers:
        console.print("[yellow]Aucune offre récupérée.[/yellow]")
        return

    unique = deduplicate(all_offers)
    dup_count = len(all_offers) - len(unique)
    filtered = [apply_filter(o) for o in unique]

    new_count = sum(1 for o in filtered if db.upsert_offer(o))
    known_count = len(filtered) - new_count

    console.print(
        f"\n[bold green]{new_count} nouvelles offres[/bold green] enregistrées  "
        f"[dim]({known_count} déjà connues, {dup_count} doublons supprimés)[/dim]"
    )
    suspicious = sum(1 for o in filtered if o.suspicion_score >= 0.5)
    if suspicious:
        console.print(f"[yellow]  ⚠  {suspicious} offres marquées suspectes (score ≥ 0.5)[/yellow]")


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------

def cmd_review(args):
    db = _get_db()
    try:
        status_filter = OfferStatus(args.status)
    except ValueError:
        console.print(f"[red]Statut inconnu : {args.status}[/red]")
        return

    max_sus = None if args.all else 0.9  # masquer les pièges évidents sauf si --all
    offers = db.get_offers(status=status_filter, max_suspicion=max_sus)

    if not offers:
        console.print(f"[yellow]Aucune offre avec le statut « {status_filter.value} ».[/yellow]")
        return

    console.print(
        f"\n[bold]{len(offers)} offre(s)[/bold] — statut : [cyan]{status_filter.value}[/cyan]"
        + (" [dim](pièges évidents masqués, utilisez --all pour tout voir)[/dim]" if not args.all else "")
    )
    console.print("[dim]Commandes : Entrée=vu suivant  a=postuler  x=ignorer  o=ouvrir  q=quitter[/dim]\n")

    for offer in offers:
        _render_offer(offer)
        action = Prompt.ask("[dim]>[/dim]", default="").strip().lower()

        if action == "a":
            notes = Prompt.ask("  Notes (optionnel)", default="")
            db.add_application(Application(offer_id=offer.id, notes=notes))
            console.print("  [green]Candidature enregistrée.[/green]")
        elif action == "x":
            db.update_status(offer.id, OfferStatus.SKIPPED)
            console.print("  [dim]Ignorée.[/dim]")
        elif action == "o":
            if offer.url:
                webbrowser.open(offer.url)
                console.print("  [dim]Ouverture dans le navigateur…[/dim]")
            else:
                console.print("  [yellow]Pas d'URL disponible.[/yellow]")
            # Rester sur la même offre pour permettre une action après avoir lu
            action2 = Prompt.ask("[dim]>[/dim]", default="").strip().lower()
            if action2 == "a":
                notes = Prompt.ask("  Notes (optionnel)", default="")
                db.add_application(Application(offer_id=offer.id, notes=notes))
                console.print("  [green]Candidature enregistrée.[/green]")
            elif action2 == "x":
                db.update_status(offer.id, OfferStatus.SKIPPED)
            elif action2 == "q":
                break
            else:
                db.update_status(offer.id, OfferStatus.SEEN)
        elif action == "q":
            break
        else:
            # Entrée vide ou toute autre touche = vu, on passe
            db.update_status(offer.id, OfferStatus.SEEN)

        console.print()


def _render_offer(offer: Offer):
    if offer.suspicion_score >= 0.6:
        border = "red"
        badge = f"[red bold]⚠ SUSPECT {offer.suspicion_score:.0%}[/red bold]"
    elif offer.suspicion_score >= 0.3:
        border = "yellow"
        badge = f"[yellow]⚠ {offer.suspicion_score:.0%}[/yellow]"
    else:
        border = "blue"
        badge = ""

    date_str = offer.posted_at.strftime("%d/%m/%Y") if offer.posted_at else "date inconnue"
    salary_str = f" · {offer.salary}" if offer.salary else ""

    # Utiliser un objet Text pour que Rich n'interprète jamais le contenu
    # utilisateur comme du markup, quel que soit son contenu.
    body = Text()
    body.append(f"{offer.source} · {date_str}{salary_str}", style="dim")
    if offer.url:
        url_display = offer.url[:90] + ("…" if len(offer.url) > 90 else "")
        body.append(f"\n{url_display}", style=f"dim link {offer.url}")
    body.append("\n\n")
    desc = offer.description[:600]
    if len(offer.description) > 600:
        desc += "…"
    body.append(desc)
    if offer.suspicion_reasons:
        joined = " · ".join(offer.suspicion_reasons[:3])
        body.append(f"\nRaisons : {joined}", style="dim yellow")

    title_line = (
        f"[bold]{escape(offer.title)}[/bold]  "
        f"[dim]{escape(offer.company)} · {escape(offer.location)}[/dim]  "
        f"{badge}"
    )
    console.print(Panel(body, title=title_line, title_align="left", border_style=border))


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def cmd_stats(args):
    db = _get_db()
    stats = db.get_stats()

    status_labels = {
        "new": "Nouvelles",
        "seen": "Vues",
        "applied": "Candidatures envoyées",
        "skipped": "Ignorées",
        "rejected": "Refusées",
    }

    t_status = Table(title="Par statut", box=box.ROUNDED, show_header=True)
    t_status.add_column("Statut", style="cyan")
    t_status.add_column("Nombre", justify="right", style="bold")
    for status, count in stats.get("by_status", {}).items():
        t_status.add_row(status_labels.get(status, status), str(count))

    t_source = Table(title="Par source", box=box.ROUNDED, show_header=True)
    t_source.add_column("Source", style="cyan")
    t_source.add_column("Nombre", justify="right", style="bold")
    for source, count in stats.get("by_source", {}).items():
        t_source.add_row(source, str(count))

    console.print(t_status)
    console.print(t_source)
    console.print(
        f"\n[bold]Candidatures totales :[/bold] {stats['total_applications']}"
    )


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Alternance Tracker — agrégateur d'offres dev web/app sur Grenoble"
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMANDE")

    sub.add_parser("init", help="Configurer le .env interactivement (clés API, ville, rayon)")

    p_fetch = sub.add_parser("fetch", help="Récupérer les nouvelles offres")
    p_fetch.add_argument(
        "--ft",
        action="store_true",
        help="Inclure France Travail (nécessite FT_CLIENT_ID/FT_CLIENT_SECRET dans .env)",
    )

    p_review = sub.add_parser("review", help="Passer en revue les offres")
    p_review.add_argument(
        "--status",
        default="new",
        choices=[s.value for s in OfferStatus],
        help="Filtrer par statut (défaut: new)",
    )
    p_review.add_argument(
        "--all",
        action="store_true",
        help="Afficher aussi les offres très suspectes (score > 0.9)",
    )

    sub.add_parser("stats", help="Afficher les statistiques")

    args = parser.parse_args()

    if args.command == "init":
        run_init_wizard()
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "review":
        cmd_review(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
