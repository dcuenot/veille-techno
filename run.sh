#!/bin/bash
set -e

echo "=== Veille Techno add-on starting ==="

OPTIONS_FILE="/data/options.json"

# Read options via jq
ANTHROPIC_API_KEY=$(jq -r '.anthropic_api_key' "$OPTIONS_FILE")
AWS_ACCESS_KEY_ID=$(jq -r '.aws_access_key_id' "$OPTIONS_FILE")
AWS_SECRET_ACCESS_KEY=$(jq -r '.aws_secret_access_key' "$OPTIONS_FILE")
AWS_DEFAULT_REGION=$(jq -r '.aws_default_region' "$OPTIONS_FILE")
OWM_API_KEY=$(jq -r '.owm_api_key' "$OPTIONS_FILE")
SCHEDULE_HOUR=$(jq -r '.schedule_hour' "$OPTIONS_FILE")
SCHEDULE_MINUTE=$(jq -r '.schedule_minute' "$OPTIONS_FILE")

export ANTHROPIC_API_KEY
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION
export OWM_API_KEY

# HA API access via Supervisor (auto-injected)
export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"

# Generate settings.yaml from add-on options
POLLY_VOICE=$(jq -r '.polly_voice' "$OPTIONS_FILE")
WEATHER_CITY=$(jq -r '.weather_city' "$OPTIONS_FILE")
WEATHER_LAT=$(jq -r '.weather_lat' "$OPTIONS_FILE")
WEATHER_LON=$(jq -r '.weather_lon' "$OPTIONS_FILE")
MEDIA_PLAYER=$(jq -r '.media_player_entity' "$OPTIONS_FILE")
EDITOR_MODEL=$(jq -r '.editor_model' "$OPTIONS_FILE")
MAX_GENERAL=$(jq -r '.max_general_news' "$OPTIONS_FILE")
MAX_TECH=$(jq -r '.max_tech_news' "$OPTIONS_FILE")
LOG_LEVEL=$(jq -r '.log_level' "$OPTIONS_FILE")

mkdir -p /app/config /app/output /app/logs /media/veille-techno

cat > /app/config/settings.yaml << YAML
timezone: "Europe/Paris"

weather:
  city: "${WEATHER_CITY}"
  lat: ${WEATHER_LAT}
  lon: ${WEATHER_LON}

editor:
  model: "${EDITOR_MODEL}"
  max_general_news: ${MAX_GENERAL}
  max_tech_news: ${MAX_TECH}

audio:
  engine: "polly"
  voice: "${POLLY_VOICE}"
  output_dir: "/app/output"
  retention_days: 7

publisher:
  ha_media_dir: "/media/veille-techno"
  media_player_entity: "${MEDIA_PLAYER}"

logging:
  level: "${LOG_LEVEL}"
  log_dir: "/app/logs"

sources:
  - name: "Le Monde"
    type: "rss"
    category: "general"
    url: "https://www.lemonde.fr/rss/une.xml"
  - name: "France Info"
    type: "rss"
    category: "general"
    url: "https://www.francetvinfo.fr/titres.rss"
  - name: "BBC News"
    type: "rss"
    category: "general"
    url: "https://feeds.bbci.co.uk/news/rss.xml"
  - name: "Hacker News"
    type: "hackernews"
    category: "tech"
    url: ""
  - name: "TechCrunch"
    type: "rss"
    category: "tech"
    url: "https://techcrunch.com/feed/"
  - name: "Lobsters"
    type: "rss"
    category: "tech"
    url: "https://lobste.rs/rss"
  - name: "Ars Technica"
    type: "rss"
    category: "tech"
    url: "https://feeds.arstechnica.com/arstechnica/index"
  - name: "GitHub Trending"
    type: "github_trending"
    category: "tech"
    url: ""
YAML

echo "Configuration generated"
echo "Schedule: every day at ${SCHEDULE_HOUR}:${SCHEDULE_MINUTE}"

# Run once at startup
echo "Running initial briefing..."
cd /app && python3 -m src.orchestrator --config config/settings.yaml 2>&1 || true

# Set up cron
CRON_LINE="${SCHEDULE_MINUTE} ${SCHEDULE_HOUR} * * * cd /app && ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION} OWM_API_KEY=${OWM_API_KEY} HA_URL=${HA_URL} HA_TOKEN=${HA_TOKEN} python3 -m src.orchestrator --config config/settings.yaml >> /app/logs/cron.log 2>&1"

echo "${CRON_LINE}" | crontab -

echo "Cron scheduled. Waiting..."

# Keep container alive and run cron in foreground
crond -f
