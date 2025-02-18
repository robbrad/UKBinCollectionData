ARG VARIANT="3.12-bullseye"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT} AS ukbc-dev-base

USER root

# Install dependencies for Google Chrome
RUN dpkg --add-architecture amd64 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg2 \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    unzip \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libudev1 \
    libvulkan1 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libcurl4 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update

# Install Chrome
RUN apt-get install -y google-chrome-stable && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | sed 's/Google Chrome //' | tr -d ' ') && \
    wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    rm -rf /tmp/chromedriver* && \
    chmod +x /usr/local/bin/chromedriver

USER vscode

# Define the version of Poetry to install (default is 1.4.2)
# Define the directory of python virtual environment
ARG PYTHON_VIRTUALENV_HOME=/home/vscode/ukbc-py-env \
    POETRY_VERSION=1.8.4

ENV POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=true

# Install Poetry outside of the virtual environment to avoid conflicts
RUN python3 -m pip install --user pipx && \
    python3 -m pipx ensurepath && \
    pipx install poetry==${POETRY_VERSION}

# Create a Python virtual environment for the project
RUN python3 -m venv ${PYTHON_VIRTUALENV_HOME} && \
    $PYTHON_VIRTUALENV_HOME/bin/pip install --upgrade pip

ENV PATH="$PYTHON_VIRTUALENV_HOME/bin:$PATH" \
    VIRTUAL_ENV=$PYTHON_VIRTUALENV_HOME

# Setup for bash
RUN poetry completions bash >> /home/vscode/.bash_completion && \
    echo "export PATH=$PYTHON_VIRTUALENV_HOME/bin:$PATH" >> ~/.bashrc

# Set the working directory for the app
WORKDIR /ukbc_build

# Use a multi-stage build to install dependencies
FROM ukbc-dev-base AS ukbc-dev-dependencies

ARG PYTHON_VIRTUALENV_HOME

COPY . /ukbc_build/

RUN poetry install --no-interaction --no-ansi --with dev

#docker build -f .devcontainer/dev.Dockerfile -t ukbc_dev_container .
