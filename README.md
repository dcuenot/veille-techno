# Veille Techno

Briefing matinal audio automatise — collecte de news, editorialisation par IA, synthese vocale, diffusion sur Amazon Echo via Home Assistant.

## Installation (Add-on Home Assistant)

### Prerequis

- Home Assistant OS sur Raspberry Pi (ou autre)
- Alexa Media Player installe via HACS
- Cles API : Anthropic, AWS (Polly + S3), OpenWeatherMap

### Installation

1. Depuis le terminal SSH de HA :

```bash
cd /addons
git clone <repo-url> veille_techno
```

2. Dans HA : **Settings > Add-ons > Recharger** (bouton en haut a droite)
3. L'add-on "Veille Techno" apparait dans **Add-ons locaux**
4. Cliquer > **Installer**
5. Onglet **Configuration** : remplir les cles API et parametres
6. **Demarrer** l'add-on

### Configuration

| Parametre | Description |
|-----------|-------------|
| `anthropic_api_key` | Cle API Anthropic (console.anthropic.com) |
| `aws_access_key_id` | AWS IAM avec policy AmazonPollyReadOnlyAccess + S3 |
| `aws_secret_access_key` | Secret AWS |
| `owm_api_key` | Cle OpenWeatherMap (gratuit) |
| `weather_city` / `weather_lat` / `weather_lon` | Localisation meteo |
| `s3_bucket` | Bucket S3 pour heberger les MP3 |
| `polly_voice` | Voix Polly (defaut: Lea) |
| `editor_model` | Modele Claude (defaut: claude-haiku-4-5-20251001) |
| `max_general_news` / `max_tech_news` | Nombre de news par categorie |

### Commandes stdin

L'add-on ecoute les commandes via `hassio.addon_stdin` :

| Commande | Description |
|----------|-------------|
| `prepare` | Collecte les news, genere le briefing audio, upload sur S3 |
| `play` | Joue le briefing sur les entites configurees |
| `play:entity1,entity2` | Joue sur des entites specifiques (override config) |

### Automatisations HA

#### Prerequis : helpers HA

Creer deux helpers dans **Parametres > Appareils & services > Helpers** :

- `input_datetime.iphone_alarm_datetime` (heure uniquement, pas de date)
- `input_boolean.iphone_alarm_turn_on`

Ces helpers peuvent etre mis a jour via un Raccourci iOS qui envoie l'heure d'alarme a HA.

#### 1. Prepare (30 min avant le reveil)

```yaml
alias: "Veille Techno - Prepare"
trigger:
  - platform: template
    value_template: >
      {% set alarm = states('input_datetime.iphone_alarm_datetime').split(':') %}
      {% set alarm_min = alarm[0]|int * 60 + alarm[1]|int %}
      {% set now_min = now().hour * 60 + now().minute %}
      {{ now_min == alarm_min - 30 }}
condition:
  - condition: state
    entity_id: input_boolean.iphone_alarm_turn_on
    state: "on"
action:
  - service: hassio.addon_stdin
    data:
      addon: local_veille_techno
      input: prepare
```

#### 2. Play (a l'heure du reveil)

```yaml
alias: "Veille Techno - Play"
trigger:
  - platform: time
    at: input_datetime.iphone_alarm_datetime
condition:
  - condition: state
    entity_id: input_boolean.iphone_alarm_turn_on
    state: "on"
action:
  - service: media_player.volume_set
    target:
      entity_id:
        - media_player.chambre
        - media_player.salle_de_bain
    data:
      volume_level: 0.5
  - service: hassio.addon_stdin
    data:
      addon: local_veille_techno
      input: "play:media_player.chambre,media_player.salle_de_bain"
```

#### 3. Spotify apres le briefing

```yaml
alias: "Veille Techno - Spotify"
trigger:
  - platform: event
    event_type: veille_techno_play_done
action:
  - service: media_player.volume_set
    target:
      entity_id:
        - media_player.chambre
        - media_player.salle_de_bain
    data:
      volume_level: 0.3
  - service: media_player.play_media
    target:
      entity_id: media_player.chambre
    data:
      media_content_id: "Mes favoris sur Spotify"
      media_content_type: custom
```

## Developpement local

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/settings.example.yaml config/settings.yaml
```

### Tests

```bash
source .venv/bin/activate
python -m pytest --cov=src --cov-report=term-missing -v
```

### Dry-run

```bash
python -m src.orchestrator --dry-run --config config/settings.yaml
```

## Cout estime

~6 EUR/mois (Claude Haiku + Amazon Polly). Polly gratuit la premiere annee (Free Tier).
