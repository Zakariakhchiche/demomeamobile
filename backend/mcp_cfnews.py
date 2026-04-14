"""
Serveur MCP pour la veille CFNEWS.
Scrape les titres d'actualité de cfnews.net et extrait les noms d'entreprises.
Usage : python mcp_cfnews.py (mode stdio pour Claude Code)
"""

import re
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-cfnews")

CFNEWS_BASE_URL = "https://www.cfnews.net"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
}

mcp = FastMCP(
    "cfnews-veille",
    instructions="Serveur MCP de veille sur CFNEWS.net - actualités M&A, LBO, levées de fonds",
)


def _fetch_page(url: str, retries: int = 2) -> BeautifulSoup | None:
    """Récupère et parse une page HTML avec retry sur erreur 503."""
    import time
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            logger.error("Erreur fetch %s (tentative %d) : %s", url, attempt + 1, e)
            if attempt < retries and "503" in str(e):
                time.sleep(2 * (attempt + 1))
                continue
            return None


def _extract_articles(soup: BeautifulSoup | None) -> list[dict]:
    """Extrait les articles depuis la page d'accueil cfnews."""
    if soup is None:
        return []
    articles = []
    seen_titles = set()

    # Stratégie 1 : liens vers /L-actualite/ contenant des titres
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "/L-actualite/" not in href:
            continue

        # On cherche les liens qui ont un texte substantiel (titres d'articles)
        text = link.get_text(strip=True)
        if not text or len(text) < 10:
            continue

        # Nettoyer le texte : enlever les dates et catégories collées au début
        # Pattern : "14/04/2026Capital développementTra-C Industrie..."
        text = re.sub(
            r"^\d{1,2}/\d{2}/\d{4}"
            r"(?:Capital[ -]?(?:innovation|développement|développement|transmission)|"
            r"M&A Corporate|International|Nominations|"
            r"Marche General|Marché Général|"
            r"Private Equity|Dette|Infra|Immobilier|"
            r"Retournement|Services financiers|"
            r"[A-ZÀ-Ü][a-zà-ü]+(?:\s+[a-zà-ü]+)*)",
            "", text
        ).strip()
        # Nettoyer le préfixe "TECH |" ou similaire
        text = re.sub(r"^(?:TECH|IMMO|INFRA)\s*\|?\s*", "", text).strip()
        if not text or len(text) < 10:
            continue

        # Filtrer les liens de navigation (catégories simples)
        # Un titre d'article est généralement plus long qu'un nom de catégorie
        path_parts = [p for p in href.split("/") if p]
        if len(path_parts) < 4:
            continue

        # Extraire l'ID numérique en fin d'URL (signature d'un article)
        id_match = re.search(r"-(\d{5,7})$", href)
        if not id_match:
            continue

        article_id = id_match.group(1)
        # Déduplication par ID d'article (plusieurs liens peuvent pointer vers le même article)
        if article_id in seen_titles:
            continue
        seen_titles.add(article_id)

        # Extraire la catégorie depuis l'URL
        category = _extract_category(href)

        # Extraire le nom d'entreprise depuis le titre
        company = _extract_company_from_title(text)

        # Chercher la date dans les éléments voisins
        date_str = _find_date_near(link)

        full_url = href if href.startswith("http") else f"{CFNEWS_BASE_URL}{href}"

        articles.append({
            "id": article_id,
            "titre": text,
            "entreprise": company,
            "categorie": category,
            "date": date_str,
            "url": full_url,
        })

    return articles


def _extract_category(href: str) -> str:
    """Extrait la catégorie depuis l'URL d'un article."""
    parts = [p for p in href.split("/") if p]
    # /L-actualite/Capital-developpement/Operations/...
    if len(parts) >= 2:
        cat = parts[1].replace("-", " ")
        return cat
    return "Non classé"


def _extract_company_from_title(title: str) -> str:
    """Tente d'extraire le nom de l'entreprise depuis le titre.

    Les titres cfnews suivent souvent le pattern :
    - "NomEntreprise verbe ..." (ex: "Tra-C Industrie soude son capital")
    - "NomEntreprise : description"
    """
    # Pattern : tout ce qui précède un verbe courant en M&A
    verbs = (
        r"\b(?:soude|lève|accélère|acquiert|cède|rejoint|lance|ouvre|signe|"
        r"renforce|rachète|investit|entre|sort|finalise|se|prépare|annonce|"
        r"boucle|change|communique|déploie|double|entre|fait|monte|obtient|"
        r"passe|poursuit|prend|réalise|s'offre|tisse|vise|grandit|"
        r"consolide|développe|finance|lâche|négocie|noue|opère|"
        r"scelle|structure|transforme|valorise|envisage|étend|"
        r"choisit|conclut|confie|confirme|crée|décroche|dévoile|"
        r"élargit|embauche|engage|explore|ferme|fusionne|gagne|"
        r"innove|intègre|lève|mise|modernise|muscle|nourrit|"
        r"pilote|pivote|porte|pousse|progresse|propose|recrute|"
        r"redresse|reprend|revient|séduit|sur-performe|traverse|"
        r"triple|vend|atteint|capte|clôt|construit|convertit|"
        r"déménage|démarre|distribue|émet|essaime|étale|exporte|"
        r"frappe|hérite|implante|importe|inaugure|libère|loge|"
        r"maintient|marque|multiplie|ouvre|parie|partage|"
        r"perçoit|plonge|produit|profite|projette|protège|"
        r"récolte|réduit|relance|rembourse|remporte|renouvelle|"
        r"restructure|sauve|surveille|unifie|valide|vole|croit|"
        r"affiche|amplifie|capitalise|entame)\b"
    )

    match = re.match(rf"^(.+?)\s+{verbs}", title, re.IGNORECASE)
    if match:
        company = match.group(1).strip().rstrip(",:-")
        if _is_valid_company(company):
            return company

    # Pattern : "Titre : description"
    if " : " in title:
        candidate = title.split(" : ")[0].strip()
        if _is_valid_company(candidate):
            return candidate

    # Pattern : texte avant une virgule
    if ", " in title:
        candidate = title.split(", ")[0].strip()
        if _is_valid_company(candidate):
            return candidate

    # Fallback : premiers mots (souvent le nom de l'entreprise)
    words = title.split()
    if len(words) >= 2:
        # Prendre les mots qui commencent par une majuscule au début
        company_words = []
        for w in words:
            if w[0].isupper() or w in ("de", "du", "des", "la", "le", "les", "et", "&", "-"):
                company_words.append(w)
            else:
                break
        if company_words:
            candidate = " ".join(company_words)
            if _is_valid_company(candidate):
                return candidate

    return ""


def _is_valid_company(name: str) -> bool:
    """Vérifie si le texte extrait ressemble à un nom d'entreprise valide."""
    if not name or len(name) < 2 or len(name) > 60:
        return False
    # Rejeter les faux positifs courants
    reject_patterns = [
        r"^(Un|Une|Le|La|Les|Des|Du|De|Deux|Trois|Quatre|Cinq|Six|Sept|Huit|Neuf|Dix|Mid)$",
        r"^(Un|Une|Le|La|Les|Des|Du)\s+(fonds?|étude|rapport|executive|nouveau|expert|conseil)",
        r"^(Selon|Fort de|Comment|Correction|Décès|Closing|Valorisation|Budget|Mid cap)",
        r"^(Private Equity|Dette|Reprises|IPEV|Tête|TECH)",
        r"^(Investir|Partage|Pacte|Fonds de)",
        r"\d{2}/\d{2}/\d{4}",
    ]
    for pattern in reject_patterns:
        if re.match(pattern, name, re.IGNORECASE):
            return False
    return True


def _find_date_near(element) -> str:
    """Cherche une date dans les éléments proches du lien."""
    # Remonter au parent et chercher du texte de date
    parent = element.parent
    for _ in range(3):
        if parent is None:
            break
        text = parent.get_text(" ", strip=True)
        date_match = re.search(
            r"(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|"
            r"août|septembre|octobre|novembre|décembre)\s+\d{4})",
            text, re.IGNORECASE
        )
        if date_match:
            return date_match.group(1)
        parent = parent.parent
    return ""


@mcp.tool()
def cfnews_actualites(categorie: str = "", limite: int = 20) -> list[dict]:
    """Récupère les dernières actualités de CFNEWS.net (M&A, LBO, levées de fonds).

    Scrape la page d'accueil et extrait les titres, noms d'entreprises et catégories.

    Args:
        categorie: Filtrer par catégorie (ex: "Capital développement", "M A Corporate", "Capital innovation"). Vide = toutes.
        limite: Nombre maximum d'articles à retourner (défaut: 20).

    Returns:
        Liste d'articles avec: id, titre, entreprise, categorie, date, url
    """
    soup = _fetch_page(CFNEWS_BASE_URL)
    if soup is None:
        return [{"erreur": "Impossible de charger cfnews.net"}]

    articles = _extract_articles(soup)

    if categorie:
        cat_lower = categorie.lower()
        articles = [
            a for a in articles
            if cat_lower in a["categorie"].lower()
        ]

    return articles[:limite]


@mcp.tool()
def cfnews_recherche_entreprise(nom_entreprise: str) -> list[dict]:
    """Recherche une entreprise spécifique dans les actualités CFNEWS.

    Scrape cfnews.net et filtre les articles mentionnant l'entreprise.

    Args:
        nom_entreprise: Nom de l'entreprise à rechercher (ex: "Doctolib", "Tra-C Industrie")

    Returns:
        Liste d'articles mentionnant cette entreprise.
    """
    soup = _fetch_page(CFNEWS_BASE_URL)
    if soup is None:
        return [{"erreur": "Impossible de charger cfnews.net"}]

    articles = _extract_articles(soup)
    nom_lower = nom_entreprise.lower()

    results = [
        a for a in articles
        if nom_lower in a["titre"].lower() or nom_lower in a["entreprise"].lower()
    ]

    return results if results else [{"info": f"Aucun article trouvé pour '{nom_entreprise}' dans les actualités récentes"}]


@mcp.tool()
def cfnews_entreprises_mentionnees() -> list[dict]:
    """Liste toutes les entreprises mentionnées dans les titres d'actualité CFNEWS.

    Utile pour identifier rapidement quelles sociétés font l'actualité M&A du jour.

    Returns:
        Liste des entreprises avec leur catégorie et le titre associé.
    """
    soup = _fetch_page(CFNEWS_BASE_URL)
    if soup is None:
        return [{"erreur": "Impossible de charger cfnews.net"}]

    articles = _extract_articles(soup)

    entreprises = []
    seen = set()
    for a in articles:
        name = a["entreprise"]
        if name and name not in seen:
            seen.add(name)
            entreprises.append({
                "entreprise": name,
                "categorie": a["categorie"],
                "titre": a["titre"],
                "url": a["url"],
            })

    return entreprises


@mcp.tool()
def cfnews_detail_article(url_article: str) -> dict:
    """Récupère le contenu détaillé d'un article CFNEWS.

    Args:
        url_article: URL complète de l'article CFNEWS (ex: https://www.cfnews.net/L-actualite/...)

    Returns:
        Contenu de l'article avec titre, contenu texte et métadonnées.
    """
    if not url_article.startswith(CFNEWS_BASE_URL):
        return {"erreur": "URL non valide - doit être une URL cfnews.net"}

    soup = _fetch_page(url_article)
    if soup is None:
        return {"erreur": f"Impossible de charger l'article : {url_article}"}

    # Extraire le titre principal
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Extraire le contenu textuel
    content_parts = []
    # Chercher les paragraphes dans le corps de l'article
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 20:
            content_parts.append(text)

    # Extraire les métadonnées (catégorie, date, etc.)
    meta = {}
    date_match = re.search(
        r"(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|"
        r"août|septembre|octobre|novembre|décembre)\s+\d{4})",
        soup.get_text(), re.IGNORECASE
    )
    if date_match:
        meta["date"] = date_match.group(1)

    return {
        "titre": title,
        "url": url_article,
        "contenu": "\n\n".join(content_parts[:15]),
        "meta": meta,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
