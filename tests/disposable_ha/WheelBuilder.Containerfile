ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}

COPY tests/disposable_ha/build-1.3.0-py3-none-any.whl /tmp/wheelhouse/
COPY tests/disposable_ha/packaging-26.2-py3-none-any.whl /tmp/wheelhouse/
COPY tests/disposable_ha/poetry_core-1.9.1-py3-none-any.whl /tmp/wheelhouse/
COPY tests/disposable_ha/pyproject_hooks-1.2.0-py3-none-any.whl /tmp/wheelhouse/
RUN PIP_NO_INDEX=1 python -m pip install --no-deps /tmp/wheelhouse/*.whl \
    && rm -rf /tmp/wheelhouse

COPY . /workspace
WORKDIR /workspace
RUN python -m build --wheel --no-isolation --outdir /dist

LABEL org.opencontainers.image.title="UKBCD disposable offline wheel builder"
LABEL org.opencontainers.image.source="local-only"
