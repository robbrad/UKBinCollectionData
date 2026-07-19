ARG CANDIDATE_IMAGE
FROM ${CANDIDATE_IMAGE}

COPY tests/disposable_ha/live_canary_runner.py /opt/ukbcd/live_canary_runner.py

ENV PYTHONDONTWRITEBYTECODE=1
USER 1000:1000
ENTRYPOINT ["python", "/opt/ukbcd/live_canary_runner.py", "--confirm-one-public-fixture-lookup"]

LABEL org.opencontainers.image.title="UKBCD one-shot South Kesteven canary"
LABEL org.opencontainers.image.source="local-only"
