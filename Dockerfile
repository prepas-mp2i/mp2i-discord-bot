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

# Set a working directory
WORKDIR /bot

# Copy the source code into the image
COPY . .

# Install the dependencies
RUN pipenv lock \
    && pipenv install --clear --system \
    && pipenv --clear

# Run the bot
CMD ["python", "-m", "mp2i"]
