ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}

COPY . /workspace
WORKDIR /workspace

# Image construction is the controlled dependency-preparation window.  Test
# execution happens later with --network none against this frozen image.
RUN python -m pip install --disable-pip-version-check \
        . \
        pytest==9.0.2 \
        pytest-asyncio==1.3.0 \
        pytest-freezer==0.4.9

LABEL org.opencontainers.image.title="UKBCD disposable Python compatibility gate"
LABEL org.opencontainers.image.source="local-only"
