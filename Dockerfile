FROM python:3.9-slim-buster
# slim=debian-based. Not using alpine because it has poor python3 support.

# Set pip to have cleaner logs
ENV PYTHONUNBUFFERED=1 \
    PIPENV_NOSPIN=1
# Configure timezone
ENV TZ Europe/Paris

# Install git and Pipenv
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends git \
    && pip install -U pipenv \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY Pipfile* ./
RUN pipenv lock && pipenv --clear && pipenv --rm
RUN pipenv install --system

# Set a working directory
WORKDIR /MP2I
# Copy the source code into the image
COPY . .
# Run the bot
CMD ["python", "-m", "mp2i"]