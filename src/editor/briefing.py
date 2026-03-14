from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from src.collector.base import Article
from src.weather.forecast import WeatherData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un presentateur de briefing matinal francophone. Ton ton est informe, accessible et naturel.

Tu recois une liste d'articles et des donnees meteo. Tu dois produire un briefing audio structure en segments JSON.

REGLES :
- Phrases courtes, adaptees a l'oral (pas de lecture)
- Pas de jargon non explique
- Pas d'URLs
- Transitions naturelles entre les sujets
- Le briefing doit durer environ 10 a 15 minutes a la lecture
- Les articles marques [PRIORITAIRE] proviennent de sources de confiance (curation humaine). Privilegie-les dans ta selection tech, sauf s'ils sont redondants avec d'autres articles deja selectionnes.

FORMAT DE SORTIE (JSON strict) :
{
  "segments": [
    {"type": "intro", "text": "Bonjour, c'est [jour] [date], voici votre briefing du matin."},
    {"type": "weather", "text": "Cote meteo a [ville], [conditions]."},
    {"type": "news", "text": "Dans l'essentiel aujourd'hui. [transition et resume du 1er sujet actu generale]"},
    {"type": "news", "text": "[transition et resume du 2e sujet actu generale]"},
    {"type": "news", "text": "Cote tech maintenant. [transition et resume du 1er sujet tech]"},
    {"type": "news", "text": "[transition et resume du 2e sujet tech]"},
    {"type": "outro", "text": "Bonne journee, et a demain."}
  ]
}

IMPORTANT : Chaque article doit etre dans son propre segment "news" (un segment = un sujet). Cela permet d'inserer des pauses entre les sujets.

IMPORTANT : Retourne UNIQUEMENT du JSON valide, sans commentaire ni markdown."""

MAX_RETRIES = 2


@dataclass(frozen=True)
class BriefingSegment:
    type: str  # "intro", "weather", "news", "outro"
    text: str


def generate_briefing(
    articles: list[Article],
    weather: WeatherData | None,
    api_key: str,
    model: str,
    max_general_news: int,
    max_tech_news: int,
) -> list[BriefingSegment]:
    """Generate editorialized briefing segments via Claude API."""
    client = anthropic.Anthropic(api_key=api_key)

    user_content = _build_user_prompt(
        articles, weather, max_general_news, max_tech_news
    )

    for attempt in range(MAX_RETRIES):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = _extract_json(message.content[0].text)
            data = json.loads(raw)
            return [
                BriefingSegment(type=s["type"], text=s["text"])
                for s in data["segments"]
            ]
        except (json.JSONDecodeError, KeyError, IndexError, anthropic.APIError) as e:
            logger.warning(
                "Briefing error (attempt %d): %s — raw response: %.200s",
                attempt + 1, e, raw if "raw" in dir() else "N/A",
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError("Failed to generate briefing after retries")


def _extract_json(text: str) -> str:
    """Strip markdown code fences if present."""
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def _build_user_prompt(
    articles: list[Article],
    weather: WeatherData | None,
    max_general_news: int,
    max_tech_news: int,
) -> str:
    now = datetime.now(ZoneInfo("Europe/Paris"))
    parts = [
        f"Date : {now.strftime('%A %d %B %Y')}",
        "",
    ]

    if weather:
        parts.append("METEO :")
        parts.append(f"  Ville : {weather.city}")
        parts.append(f"  Conditions : {weather.description}")
        parts.append(
            f"  Temperature : {weather.temp_current:.0f} C "
            f"(min {weather.temp_min:.0f} C, max {weather.temp_max:.0f} C)"
        )
        parts.append("")
    else:
        parts.append("METEO : non disponible (omets le segment meteo)")
        parts.append("")

    parts.append(
        f"ARTICLES (selectionne {max_general_news} actu generale "
        f"+ {max_tech_news} tech) :"
    )
    parts.append("")

    # Sources with human curation get priority tag
    priority_sources = {"NowTech TV"}

    for i, article in enumerate(articles, 1):
        priority_tag = " [PRIORITAIRE]" if article.source in priority_sources else ""
        parts.append(
            f"{i}. [{article.category}] [{article.source}]{priority_tag} {article.title}"
        )
        parts.append(f"   Date : {article.published_at.isoformat()}")
        parts.append(f"   Resume : {article.summary}")
        parts.append("")

    return "\n".join(parts)
