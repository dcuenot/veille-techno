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

5 composants indépendants, exécutés séquentiellement par un orchestrateur.

## Composants

### 1. Collecteur de news

Récupère les articles des dernières 24h depuis des sources configurables.

**Sources :**

| Catégorie | Sources | Méthode |
|-----------|---------|---------|
| Actu France | Le Monde, France Info, Les Échos | RSS |
| Actu internationale | Reuters, BBC News | RSS |
| Tech généraliste | Hacker News, TechCrunch | API Algolia HN + RSS |
| Dev/Engineering | GitHub Trending, dev.to | Scraping HTML + RSS |
| IA/ML | Papers with Code, blogs Anthropic/OpenAI/Google DeepMind | RSS |
| Cloud/Infra | AWS What's New, Google Cloud Blog | RSS |
| Sécu | The Hacker News (security) | RSS |

**Fonctionnement :**
- Chaque source implémente une interface commune : `fetch() -> list[Article]`
- Configuration des sources via fichier YAML
- Déduplication par URL et similarité de titre (fuzzy match sur les titres, seuil 80%)
- Filtre temporel : dernières 24h uniquement (timezone Europe/Paris)
- Chaque article est tronqué à 500 caractères max pour l'extrait
- Résultat : ~30-50 articles bruts transmis à l'éditeur IA

### 2. Météo

- API OpenWeatherMap (gratuit, <1000 appels/jour)
- Localisation : Fontenay-sous-Bois (configurable dans YAML)
- Récupère : température matin/après-midi, conditions, précipitations
- Fournit un résumé court intégré dans le briefing

### 3. Éditeur IA (Claude)

Reçoit les ~30-50 articles et sélectionne les meilleurs : 3-5 actu générale + 10 tech, soit 13-15 au total. Rédige un briefing éditorialisé.

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

**Input :** Liste d'articles (titre, source, date, résumé/extrait tronqué à 500 chars) + données météo. Budget total prompt : ~20K tokens max.
**Output :** Texte brut du briefing, prêt pour le TTS. Utilisation du mode JSON (structured output) pour séparer le contenu éditorial des métadonnées, puis application d'un template SSML déterministe.

### 4. Générateur audio (Amazon Polly)

- Voix : Léa (français, Neural). Alternative : Rémi (masculin). Configurable.
- Format SSML pour le rythme : pauses entre blocs (`<break>`), emphase sur les titres
- **Chunking SSML :** Polly limite à 3 000 caractères par requête. Le texte est découpé en segments SSML valides (sans couper de balise), chaque segment est synthétisé séparément, puis les MP3 sont concaténés via pydub/ffmpeg.
- Interface commune `synthesize(text: str, voice: str) -> Path` pour permettre le swap vers ElevenLabs ou Piper.
- Sortie : fichier MP3 nommé par date (`briefing-2026-03-12.mp3`)
- Nettoyage automatique des fichiers de plus de 7 jours

### 5. Diffuseur (Home Assistant)

- Le script Python tourne sur le même Raspberry Pi que Home Assistant. Le MP3 est écrit directement dans `/config/www/briefings/` (écriture fichier locale).
- Le fichier est accessible via `http://<HA_IP>:8123/local/briefings/briefing-YYYY-MM-DD.mp3`
- Prérequis : intégration Alexa Media Player installée via HACS
- Déclenchement de la lecture par automatisation HA (capteur de présence/réveil). L'automatisation HA est **hors scope** de ce projet (l'utilisateur la configure côté HA).
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

## Résilience et gestion d'erreurs

- **Collecteur :** Si une source RSS échoue, le pipeline continue avec les sources restantes. Minimum 5 articles requis pour générer un briefing, sinon abandon avec notification.
- **Météo :** Si OpenWeatherMap est indisponible, le bloc météo est omis du briefing.
- **Claude API :** 2 tentatives avec backoff exponentiel. Si échec, pas de briefing ce jour.
- **Polly :** 2 tentatives par chunk. Si un chunk échoue, abandon avec notification.
- **Notification d'échec :** En cas d'échec du pipeline, envoi d'une notification persistante via l'API HA (service `notify`).

## Logging et observabilité

- Logging via le module `logging` Python, niveau INFO par défaut (configurable).
- Fichier de log rotatif dans `/config/logs/veille-techno.log` (rétention 7 jours).
- Chaque étape du pipeline logge sa durée d'exécution et le nombre d'éléments traités.
- En cas d'erreur : log ERROR avec traceback complet + notification HA.

## Environnement technique

- **Python :** >= 3.11
- **Gestion des dépendances :** venv + requirements.txt (pip)
- **Timezone :** Europe/Paris (configuré explicitement dans le code)
- **Dépendances principales :** feedparser, anthropic, boto3, pydub, requests, python-dotenv, pyyaml
- **Dépendance système :** ffmpeg (pour la concaténation audio via pydub)

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
- Publication en podcast RSS : possibilité d'exposer un feed RSS avec les épisodes MP3 pour écoute sur une app podcast
