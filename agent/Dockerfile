FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies and pipx
RUN apt-get update \
  && apt-get install -y curl libpq-dev \
  && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy configuration files first
COPY pyproject.toml poetry.lock* /app/

# Configure poetry and install dependencies
RUN /root/.local/bin/poetry config virtualenvs.create false \
  && /root/.local/bin/poetry install --no-interaction --no-ansi --no-root

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
  libpq-dev \
  iputils-ping \
  dnsutils \
  net-tools \
  && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code - be explicit about directories needed
COPY tui/ /app/tui/
COPY crystaldba/ /app/crystaldba/
COPY pyproject.toml /app/
COPY README.md /app/
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Install the package to register the entry points
RUN pip install -e .

# Set environment variables
ENV PYTHONPATH=/app

# Expose any necessary ports (if the TUI needs network access)
EXPOSE 8000

# Run the TUI application
# Users can pass any CLI arguments from parse_args.py:
# Example 1: Pass a database URI:
#   docker run -it --rm crystaldba-tui postgres://user:pass@host:port/dbname
# Example 2: Pass connection options:
#   docker run -it --rm crystaldba-tui -h myhost -p 5432 -U myuser -d mydb
# Example 3: Set verbosity:
#   docker run -it --rm crystaldba-tui -v dbname
ENTRYPOINT ["/app/docker-entrypoint.sh", "python", "-m", "tui.__main__"]
CMD []
