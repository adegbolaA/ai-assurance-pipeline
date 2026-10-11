# syntax=docker/dockerfile:1
# Build from the repo root:  docker build -f app/Dockerfile .
# The registry is copied in so the gateway can refuse unapproved models at startup.
#
# BASE_IMAGE is the hardened python-ml-base, pinned to the multi-arch index
# digest that hardened-base's release signed and SBOM-attested. Override for
# local builds with --build-arg BASE_IMAGE=python-ml-base:local.
ARG BASE_IMAGE=ghcr.io/platform-base-images/python-ml-base:1.0.0@sha256:0de947f5a280292c7d63fba2af2967c7444d662e7140476e7d8b2d4a665a7d4b

FROM ${BASE_IMAGE} AS builder
USER root
COPY app/requirements.txt /tmp/requirements.txt
# The venv gets no pip of its own: the base image's pip installs into it, so the
# runtime image carries no package installer (and no vendored setuptools that
# pip's bundled SBOM reports to scanners).
RUN python3 -m venv --without-pip /opt/venv && \
    pip --python /opt/venv/bin/python install --no-cache-dir --require-hashes -r /tmp/requirements.txt

FROM ${BASE_IMAGE}
LABEL org.opencontainers.image.source="https://github.com/adegbolaA/ai-assurance-pipeline"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.description="Benefits Caseworker Assistant — AI assurance pipeline reference app"

COPY --from=builder /opt/venv /opt/venv
COPY app/src /app/src
COPY app/corpus /app/corpus
COPY models/registry.yaml /app/models/registry.yaml

ENV MODEL_REGISTRY=/app/models/registry.yaml \
    PATH=/opt/venv/bin:$PATH
USER nonroot
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
