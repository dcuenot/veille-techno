ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    dcron \
    jq

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY src/ src/
COPY config/settings.example.yaml config/settings.example.yaml
COPY run.sh /

RUN chmod a+x /run.sh

ENTRYPOINT []
CMD [ "/run.sh" ]
