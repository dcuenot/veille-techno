# Veille Techno

Briefing matinal audio automatise — collecte de news, editorialisation par IA, synthese vocale, diffusion sur Amazon Echo via Home Assistant.

## Installation (Add-on Home Assistant)

### Prerequis

- Home Assistant OS sur Raspberry Pi (ou autre)
- Alexa Media Player installe via HACS
- Cles API : Anthropic, AWS (Polly), OpenWeatherMap

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
| `aws_access_key_id` | AWS IAM avec policy AmazonPollyReadOnlyAccess |
| `aws_secret_access_key` | Secret AWS |
| `owm_api_key` | Cle OpenWeatherMap (gratuit) |
| `schedule_hour` / `schedule_minute` | Heure de generation (defaut: 7h30) |
| `weather_city` / `weather_lat` / `weather_lon` | Localisation meteo |
| `media_player_entity` | Entite Echo (ex: media_player.echo_salon) |
| `polly_voice` | Voix Polly (defaut: Lea) |

### Automatisation HA (lecture sur Echo)

Creer une automatisation qui lit le MP3 quand le briefing est pret :

```yaml
automation:
  - alias: "Briefing matinal"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: template
        value_template: >
          {{ is_state('media_player.echo_salon', 'idle') }}
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.echo_salon
        data:
          volume_level: 0.5
      - service: media_player.play_media
        target:
          entity_id: media_player.echo_salon
        data:
          media_content_id: >
            media-source://media_source/local/veille-techno/briefing-{{ now().strftime('%Y-%m-%d') }}.mp3
          media_content_type: music
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
