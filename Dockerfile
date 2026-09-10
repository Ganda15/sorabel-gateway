# Image de la Sorabel Data Gateway : l'interface web, le serveur MCP qu'elle
# lance en sous-processus, et les scripts de mise en place des donnees.
#
# Pas d'extra "vector" : l'embedder livre est un hachage local et le reranker
# est lexical. Aucun modele a telecharger, donc pas de torch dans l'image.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.4"

# Les dependances d'abord, seules : cette couche ne change que si le lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Puis le code et les donnees fournies. .dockerignore ecarte le reste.
COPY . .
RUN uv sync --frozen --no-dev

# L'app ecrit ici : base SQLite generee, index documentaire, journal.
RUN mkdir -p data/index logs

COPY deploy/demarrer.sh /usr/local/bin/demarrer
RUN chmod +x /usr/local/bin/demarrer

EXPOSE 8780
CMD ["demarrer"]
