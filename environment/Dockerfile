# hash:sha256:493aebfd43423a5ce75891f6371f828645f26c01bd128e8e8bf65d821466fe9b
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/jupyterlab:3.6.1-miniconda4.12.0-python3.9-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive
ARG API_KEY
ARG API_SECRET

ARG GIT_ASKPASS
ARG GIT_ACCESS_TOKEN
COPY git-askpass /

RUN pip3 install -U --no-cache-dir \
    argparse \
    dandi \
    hdmf-zarr==0.8.0 \
    pynwb==2.8.1
