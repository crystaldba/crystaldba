FROM ubuntu:20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y --no-install-recommends \
    curl \
    wget \
    software-properties-common \
    git \
    unzip \
    make \
    libc-dev \
    gcc \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Install golang
ENV GOLANG_VERSION="1.22.1"
RUN wget -O go.tgz "https://golang.org/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz" \
    && tar -C /usr/lib -xzf go.tgz \
    && rm go.tgz

ENV PATH="/usr/lib/go/bin:${PATH}" \
    GOROOT="/usr/lib/go"

RUN mkdir -p /usr/local/crystaldba/share/collector && \
    git clone --recurse-submodules https://github.com/crystaldb/collector.git /usr/local/crystaldba/share/collector && \
    cd /usr/local/crystaldba/share/collector && \
    git checkout 95ce04683c90bc99e0e9b17a2254764c30ffc289 && \
    wget https://github.com/protocolbuffers/protobuf/releases/download/v28.2/protoc-28.2-linux-x86_64.zip && unzip protoc-28.2-linux-x86_64.zip -d protoc && \
    make build && \
    mv pganalyze-collector crystaldba-collector && \
    mv pganalyze-collector-helper crystaldba-collector-helper && \
    mv pganalyze-collector-setup crystaldba-collector-setup

COPY collector-entrypoint.sh /usr/local/crystaldba/bin/collector-entrypoint.sh
RUN chmod +x /usr/local/crystaldba/bin/collector-entrypoint.sh

WORKDIR /usr/local/crystaldba/share/collector

CMD ["/usr/local/crystaldba/bin/collector-entrypoint.sh"]
