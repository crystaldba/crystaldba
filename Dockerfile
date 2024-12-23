# SPDX-License-Identifier: Apache-2.0

FROM ubuntu:20.04 AS builder

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

# Install nvm and Node.js
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 16.17.0
RUN mkdir -p $NVM_DIR \
    && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash \
    && . $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Install golang
ENV GOLANG_VERSION="1.22.1"
RUN wget -O go.tgz "https://golang.org/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz" \
    && tar -C /usr/lib -xzf go.tgz \
    && rm go.tgz

ENV PATH="/usr/lib/go/bin:${PATH}" \
    GOROOT="/usr/lib/go"

FROM builder as release
WORKDIR /home/crystaldba
COPY ./ ./
RUN ./scripts/build.sh && \
    mkdir -p release_output && \
    mv build_output/tar.gz/crystaldba-*.tar.gz release_output/  && \
    mv build_output/tar.gz/collector-*.tar.gz release_output/  && \
    rm -rf build_output

FROM builder as lint
COPY bff/go.mod bff/go.sum ./
RUN go mod download
COPY bff/ ./
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v1.55.2
RUN cd ./solid && npx @biomejs/biome check --config-path=. .

FROM builder AS test
WORKDIR /home/crystaldba/bff
COPY bff/go.mod bff/go.sum ./
RUN go mod download
COPY bff/ ./
RUN CRYSTALDBA_ACCESS_KEY=test-access-key go test ./pkg/server -v
RUN CRYSTALDBA_ACCESS_KEY=test-access-key go test ./pkg/metrics -v
RUN CRYSTALDBA_ACCESS_KEY=test-access-key go test ./pkg/prometheus -v

WORKDIR /home/crystaldba/collector-api
COPY collector-api/go.mod collector-api/go.sum ./
RUN go mod download
COPY collector-api/ ./
RUN CRYSTALDBA_API_KEY=test-api-key go test -v ./...
