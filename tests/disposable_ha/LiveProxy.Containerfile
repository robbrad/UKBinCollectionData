ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}

COPY tests/disposable_ha/live_allowlist_proxy.py /opt/ukbcd/live_allowlist_proxy.py

ENV PYTHONDONTWRITEBYTECODE=1
USER 65532:65532
ENTRYPOINT ["python3", "/opt/ukbcd/live_allowlist_proxy.py"]
CMD ["--max-requests", "256", "--minimum-interval-ms", "25"]

LABEL org.opencontainers.image.title="UKBCD South Kesteven allowlist proxy"
LABEL org.opencontainers.image.source="local-only"
