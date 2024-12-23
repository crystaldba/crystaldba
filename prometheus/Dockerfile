FROM ubuntu:20.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install golang
ENV GOLANG_VERSION="1.22.1"
RUN wget -O go.tgz "https://golang.org/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz" \
    && tar -C /usr/lib -xzf go.tgz \
    && rm go.tgz

ENV PATH="/usr/lib/go/bin:${PATH}" \
    GOROOT="/usr/lib/go"

WORKDIR /usr/local/crystaldba

# Install Prometheus
RUN wget -qO- https://github.com/prometheus/prometheus/releases/download/v2.55.1/prometheus-2.55.1.linux-amd64.tar.gz | tar -xzf - -C /tmp/ \
    && mkdir -p ./prometheus ./config/prometheus \
    && cp /tmp/prometheus-2.55.1.linux-amd64/prometheus ./prometheus/ \
    && cp /tmp/prometheus-2.55.1.linux-amd64/promtool ./prometheus/ \
    && cp -r /tmp/prometheus-2.55.1.linux-amd64/consoles ./config/prometheus/ \
    && cp -r /tmp/prometheus-2.55.1.linux-amd64/console_libraries ./config/prometheus/ \
    && rm -rf /tmp/prometheus-2.55.1.linux-amd64

# Prometheus config
COPY prometheus.normal.yml ./config/prometheus/prometheus.normal.yml
COPY prometheus.reprocess.yml ./config/prometheus/prometheus.reprocess.yml
COPY recording_rules.yml ./config/prometheus/recording_rules.yml

# Copy and build the reloader service
COPY cmd/reloader /build/reloader
WORKDIR /build/reloader
RUN go build -o /usr/local/crystaldba/bin/prometheus-reloader

# Reset WORKDIR
WORKDIR /usr/local/crystaldba

COPY prometheus-entrypoint.sh /usr/local/crystaldba/bin/prometheus-entrypoint.sh
RUN chmod +x /usr/local/crystaldba/bin/prometheus-entrypoint.sh

CMD ["/usr/local/crystaldba/bin/prometheus-entrypoint.sh"]
