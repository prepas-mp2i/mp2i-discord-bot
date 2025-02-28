FROM python:3.9-slim-buster
# slim=debian-based. Not using alpine because it has poor python3 support.

# Set pip to have cleaner logs
ENV PYTHONUNBUFFERED=1 \
    PIPENV_NOSPIN=1

# Install git and Pipenv
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends git \
    && pip install --no-cache-dir -U pipenv \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY Pipfile* ./
RUN pipenv install --clear --system \
    && pipenv --clear

# Set a working directory
WORKDIR /home/

# Copy the source code into the image
COPY mp2i/ ./mp2i
COPY log-config.toml ./log-config.toml
COPY bot-config.yaml ./bot-config.yaml

# Run the bot
CMD ["python", "-m", "mp2i"]
