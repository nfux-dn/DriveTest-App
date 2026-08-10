FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# git is required by the runner to fetch repositories (spec section 18); curl is
# used to install the Cursor Agent CLI (the "cursor" AI provider).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the cursor-agent CLI (used headlessly by the Cursor AI provider).
RUN curl -fsS https://cursor.com/install | bash
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy the project and install it editable so the bind-mounted source (in dev)
# is the code that actually runs, enabling --reload.
COPY . .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e ".[dev]"

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
