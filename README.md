# Veille Techno

Briefing matinal audio automatise — collecte de news, editorialisation par IA, synthese vocale, diffusion sur Amazon Echo via Home Assistant.

## Installation (Raspberry Pi)

### Prerequis

- Python >= 3.11
- ffmpeg: `sudo apt install ffmpeg`
- Home Assistant avec Alexa Media Player (HACS)

### Setup

```bash
git clone <repo-url> ~/veille-techno
cd ~/veille-techno

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
cp config/settings.example.yaml config/settings.yaml
```

Editer `.env` avec vos cles API et `config/settings.yaml` avec votre configuration.

### Validation

```bash
source .venv/bin/activate
python -m src.orchestrator --dry-run --config config/settings.yaml
```

### Cron (generation quotidienne a 7h30)

```bash
crontab -e
```

Ajouter :

```
30 7 * * * cd /home/<user>/veille-techno && /home/<user>/veille-techno/.venv/bin/python -m src.orchestrator --config config/settings.yaml >> /tmp/veille-techno-cron.log 2>&1
```

### Home Assistant

Configurer une automatisation HA qui lit le MP3 sur vos Echo quand le capteur de presence/reveil se declenche :

```yaml
automation:
  - alias: "Briefing matinal"
    trigger:
      - platform: state
        entity_id: binary_sensor.alarm_clock
        to: "on"
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
            http://<HA_IP>:8123/local/briefings/briefing-{{ now().strftime('%Y-%m-%d') }}.mp3
          media_content_type: music
```

## Tests

```bash
source .venv/bin/activate
python -m pytest --cov=src --cov-report=term-missing -v
```

## Cout estime

~6 EUR/mois (Claude Haiku + Amazon Polly). Polly gratuit la premiere annee (Free Tier).
