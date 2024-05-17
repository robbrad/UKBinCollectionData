ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT} AS ukbc-dev-base

USER vscode

# Define the version of Poetry to install (default is 1.4.2)
# Define the directory of python virtual environment
ARG PYTHON_VIRTUALENV_HOME=/home/vscode/ukbc-py-env \
    POETRY_VERSION=1.5.1

ENV POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=true 

# Install Poetry outside of the v`irtual environment to avoid conflicts
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