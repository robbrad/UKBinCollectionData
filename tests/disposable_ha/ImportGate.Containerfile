ARG CANDIDATE_IMAGE
FROM ${CANDIDATE_IMAGE}

# These wheels are prepared from the exact versions in poetry.lock during the
# controlled download window.  The import gate itself is built and executed
# without network access.
COPY tests/disposable_ha/import-wheelhouse/*.whl /tmp/import-wheelhouse/
RUN PIP_NO_INDEX=1 python -m pip install --no-deps /tmp/import-wheelhouse/*.whl \
    && rm -rf /tmp/import-wheelhouse

LABEL org.opencontainers.image.title="UKBCD disposable import-all gate"
LABEL org.opencontainers.image.source="local-only"
