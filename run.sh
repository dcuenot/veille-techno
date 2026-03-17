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
S3_BUCKET=$(jq -r '.s3_bucket // ""' "$OPTIONS_FILE")
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
  s3_bucket: "${S3_BUCKET}"

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
  - name: "Les Echos Start-up"
    type: "rss"
    category: "tech"
    url: "https://services.lesechos.fr/rss/les-echos-start-up.xml"
  - name: "Les Echos Tech & Medias"
    type: "rss"
    category: "tech"
    url: "https://services.lesechos.fr/rss/les-echos-tech-medias.xml"
  - name: "Les Echos Economie"
    type: "rss"
    category: "general"
    url: "https://services.lesechos.fr/rss/les-echos-economie.xml"
  - name: "Les Echos Finance & Marches"
    type: "rss"
    category: "general"
    url: "https://services.lesechos.fr/rss/les-echos-finance-marches.xml"
  - name: "BBC News"
    type: "rss"
    category: "general"
    url: "https://feeds.bbci.co.uk/news/technology/rss.xml"
  - name: "Hacker News"
    type: "hackernews"
    category: "tech"
    url: ""
  - name: "TechCrunch"
    type: "rss"
    category: "tech"
    url: "https://techcrunch.com/feed/"
  - name: "GitHub Trending"
    type: "github_trending"
    category: "tech"
    url: ""
  - name: "dev.to"
    type: "rss"
    category: "tech"
    url: "https://dev.to/feed"
  - name: "Anthropic Blog"
    type: "rss"
    category: "tech"
    url: "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml"
  - name: "OpenAI Blog"
    type: "rss"
    category: "tech"
    url: "https://openai.com/blog/rss.xml"
  - name: "Google AI Blog"
    type: "rss"
    category: "tech"
    url: "https://blog.google/technology/ai/rss/"
  - name: "AWS What's New"
    type: "rss"
    category: "tech"
    url: "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
  - name: "Google Cloud Blog"
    type: "rss"
    category: "tech"
    url: "https://cloudblog.withgoogle.com/rss"
  - name: "The Hacker News Security"
    type: "rss"
    category: "tech"
    url: "https://feeds.feedburner.com/TheHackersNews"
  - name: "NowTech TV"
    type: "rss"
    category: "tech"
    url: "https://flipboard.com/@jkeinborg/nowtechtv-ogcbmgbby.rss"
  - name: "Korben"
    type: "rss"
    category: "tech"
    url: "https://korben.info/feed"
  - name: "Boris Cherny (Bluesky)"
    type: "rss"
    category: "tech"
    url: "https://bsky.app/profile/bcherny.bsky.social/rss"
  - name: "Arnaud Heritier (Bluesky)"
    type: "rss"
    category: "tech"
    url: "https://bsky.app/profile/aheritier.net/rss"
YAML

echo "Configuration generated"
echo "Listening for stdin commands (prepare/play triggered via HA automations)..."

# Listen on stdin for commands from HA (hassio.addon_stdin)
# Strip quotes — HA may send "play" instead of play
while read -r CMD; do
  CMD=$(echo "$CMD" | tr -d '"')
  case "$CMD" in
    play:*)
      ENTITIES="${CMD#play:}"
      echo "Received play command for entities: ${ENTITIES}"
      cd /app && python3 -m src.orchestrator --play --entities "${ENTITIES}" --config config/settings.yaml 2>&1
      ;;
    play)
      echo "Received play command"
      cd /app && python3 -m src.orchestrator --play --config config/settings.yaml 2>&1
      ;;
    prepare)
      echo "Received prepare command"
      cd /app && python3 -m src.orchestrator --prepare --config config/settings.yaml 2>&1
      ;;
    *)
      echo "Unknown command: $CMD (valid: play, prepare)"
      ;;
  esac
done
