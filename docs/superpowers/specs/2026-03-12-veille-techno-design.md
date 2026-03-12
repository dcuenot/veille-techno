# Veille Techno — Briefing matinal audio sur Amazon Echo

## Objectif

Outil de veille technologique et actualités générales qui génère chaque matin un briefing audio éditorialisé (~7-8 min), déposé sur Home Assistant et lu automatiquement sur Amazon Echo via capteur de présence/réveil.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│  Collecteur  │────▶│  Éditeur IA  │────▶│  Générateur   │────▶│  Home       │
│  RSS/APIs    │     │  (Claude)    │     │  Audio (Polly)│     │  Assistant  │
│  + Météo     │     │              │     │              │     │  → Echo     │
└─────────────┘     └──────────────┘     └───────────────┘     └─────────────┘
     7h30                7h35                 7h45                Capteur
```

4 composants indépendants, exécutés séquentiellement par un orchestrateur.

## Composants

### 1. Collecteur de news

Récupère les articles des dernières 24h depuis des sources configurables.

**Sources :**

| Catégorie | Sources | Méthode |
|-----------|---------|---------|
| Actu France | Le Monde, France Info, Les Échos | RSS |
| Actu internationale | Reuters, BBC News | RSS |
| Tech généraliste | Hacker News, TechCrunch | API HN + RSS |
| Dev/Engineering | GitHub Trending, dev.to | RSS + API GitHub |
| IA/ML | Papers with Code, blogs Anthropic/OpenAI/Google DeepMind | RSS |
| Cloud/Infra | AWS What's New, Google Cloud Blog | RSS |
| Sécu | The Hacker News (security) | RSS |

**Fonctionnement :**
- Chaque source implémente une interface commune : `fetch() -> list[Article]`
- Configuration des sources via fichier YAML
- Déduplication par URL et similarité de titre
- Filtre temporel : dernières 24h uniquement
- Résultat : ~30-50 articles bruts transmis à l'éditeur IA

### 2. Météo

- API OpenWeatherMap (gratuit, <1000 appels/jour)
- Localisation : Fontenay-sous-Bois (configurable dans YAML)
- Récupère : température matin/après-midi, conditions, précipitations
- Fournit un résumé court intégré dans le briefing

### 3. Éditeur IA (Claude)

Sélectionne les 10-15 news les plus pertinentes et rédige un briefing éditorialisé.

**Modèle :** Claude Haiku 4.5 par défaut (configurable pour Sonnet si besoin).

**Prompt système :**
- Persona : présentateur tech francophone, ton informé mais accessible
- Structure imposée :
  1. Intro : "Bonjour, c'est [jour] [date], voici votre briefing du matin."
  2. Météo : "Côté météo à Fontenay-sous-Bois, [conditions]."
  3. "L'essentiel" : 3-5 news actu France/monde avec transitions
  4. "Côté tech" : 10 news tech/dev/IA avec contexte et analyse
  5. Outro : "Bonne journée, et à demain."
- Consignes : phrases courtes adaptées à l'oral, pas de jargon non expliqué, pas d'URLs

**Input :** Liste d'articles (titre, source, date, résumé/extrait) + données météo.
**Output :** Texte brut du briefing, prêt pour le TTS.

### 4. Générateur audio (Amazon Polly)

- Voix : Léa (français, Neural). Alternative : Rémi (masculin). Configurable.
- Format SSML pour le rythme : pauses entre blocs (`<break>`), emphase sur les titres
- Sortie : fichier MP3 nommé par date (`briefing-2026-03-12.mp3`)
- Nettoyage automatique des fichiers de plus de 7 jours

### 5. Diffuseur (Home Assistant)

- Dépôt du MP3 dans `/config/www/briefings/` de Home Assistant
- Le fichier est accessible via `http://<HA_IP>:8123/local/briefings/briefing-YYYY-MM-DD.mp3`
- Prérequis : intégration Alexa Media Player installée via HACS
- Déclenchement de la lecture par automatisation HA (capteur de présence/réveil)
- Volume configurable via `media_player.volume_set`
- Multi-room possible (configurable)

## Structure du projet

```
veille-techno/
├── config/
│   ├── settings.yaml          # Sources, voix Polly, localisation météo, modèle Claude
│   └── settings.example.yaml  # Template sans secrets
├── src/
│   ├── collector/
│   │   ├── base.py            # Interface Source
│   │   ├── rss.py             # Collecteur RSS générique
│   │   ├── hackernews.py      # API Hacker News
│   │   └── github_trending.py # API GitHub
│   ├── editor/
│   │   └── briefing.py        # Génération du briefing via Claude
│   ├── weather/
│   │   └── forecast.py        # Appel OpenWeatherMap
│   ├── audio/
│   │   └── polly.py           # Génération MP3 via Amazon Polly
│   ├── publisher/
│   │   └── homeassistant.py   # Dépôt du MP3 + notification HA
│   └── orchestrator.py        # Pipeline principal
├── tests/
├── requirements.txt
├── .env.example               # ANTHROPIC_API_KEY, AWS creds, OWM key, HA token
└── README.md
```

## Scheduling

- **Génération :** Cron job à 7h30 sur le Raspberry Pi exécutant `orchestrator.py`
- **Lecture :** Automatisation Home Assistant déclenchée par capteur de présence/réveil

## Secrets et configuration

**Variables d'environnement (.env) :**
- `ANTHROPIC_API_KEY` — Clé API Claude
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — Credentials Amazon Polly
- `OWM_API_KEY` — Clé API OpenWeatherMap
- `HA_URL` / `HA_TOKEN` — URL et token longue durée Home Assistant

**Configuration (settings.yaml) :**
- Liste des sources actives et leurs URLs
- Voix Polly (nom, langue)
- Localisation météo (ville, coordonnées)
- Modèle Claude (haiku/sonnet)
- Entité media_player Echo cible
- Nombre de news par bloc
- Durée de rétention des MP3

## Estimation des coûts

| Composant | Coût mensuel |
|-----------|-------------|
| Claude API (Haiku 4.5) | ~1 € |
| Amazon Polly (Neural) | ~1-2 € |
| OpenWeatherMap | Gratuit |
| Raspberry Pi / HA | Déjà en place |
| **Total** | **~3-5 €/mois** |

## Évolutivité

- TTS swappable : architecture avec interface commune, possibilité de passer sur ElevenLabs ou Piper
- Modèle Claude configurable (Haiku → Sonnet → Opus)
- Sources ajoutables via YAML sans modification de code (pour les sources RSS)
- Format podcast RSS ajoutables en complément
