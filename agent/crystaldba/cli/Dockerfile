FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies and pipx
RUN apt-get update \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy poetry files
COPY pyproject.toml poetry.lock /app/

# Configure poetry and install dependencies
RUN /root/.local/bin/poetry config virtualenvs.create false \
    && /root/.local/bin/poetry install --no-interaction --no-ansi --no-root

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY crystaldba/ /app/crystaldba/

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port
EXPOSE ${PORT}

# Run the client application
CMD ["/usr/local/bin/python3", "-m", "crystaldba.cli.main"]
