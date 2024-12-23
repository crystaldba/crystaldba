FROM ubuntu:20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y --no-install-recommends \
    curl \
    wget \
    software-properties-common \
    libc-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install golang
ENV GOLANG_VERSION="1.22.1"
RUN wget -O go.tgz "https://golang.org/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz" \
    && tar -C /usr/lib -xzf go.tgz \
    && rm go.tgz

ENV PATH="/usr/lib/go/bin:${PATH}" \
    GOROOT="/usr/lib/go"

WORKDIR /usr/local/crystaldba

# Install promtool (required for reprocessing snapshots)
RUN wget -qO- https://github.com/prometheus/prometheus/releases/download/v2.55.1/prometheus-2.55.1.linux-amd64.tar.gz | tar -xzf - -C /tmp/ \
    && mkdir -p ./prometheus ./config/prometheus \
    && cp /tmp/prometheus-2.55.1.linux-amd64/promtool ./prometheus/ \
    && cp -r /tmp/prometheus-2.55.1.linux-amd64/consoles ./config/prometheus/ \
    && cp -r /tmp/prometheus-2.55.1.linux-amd64/console_libraries ./config/prometheus/ \
    && rm -rf /tmp/prometheus-2.55.1.linux-amd64

# Prometheus recording rules config (used for reprocessing snapshots)
COPY recording_rules.yml ./config/prometheus/recording_rules.yml

WORKDIR /usr/local/crystaldba/share/collector_api_server

# Create necessary directories
RUN mkdir -p storage

# Ensure CGO is enabled
ENV CGO_ENABLED=1
COPY ./go.mod ./go.sum ./
RUN go mod download

COPY collector-api-entrypoint.sh /usr/local/crystaldba/bin/collector-api-entrypoint.sh
RUN chmod +x /usr/local/crystaldba/bin/collector-api-entrypoint.sh

COPY ./ ./
RUN go build -o collector-api-server ./cmd/server/main.go

CMD ["/usr/local/crystaldba/bin/collector-api-entrypoint.sh"]
