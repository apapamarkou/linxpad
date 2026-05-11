# Dev container for LinxPad — Fedora-based so packaging tools match the host.
# Runs as a non-root user (devuser) for safety; Podman rootless maps this to
# your real UID on the host automatically.
FROM fedora:44

# ── System packages ──────────────────────────────────────────────────────────
# Split into logical groups so layer cache is reused when only one group changes.

# Core build + packaging tools
RUN dnf install -y \
        rpm-build \
        rpm-devel \
        rpmdevtools \
        dpkg-dev \
        git \
        make \
        which \
        findutils \
        && dnf clean all

# Python runtime + pip
RUN dnf install -y \
        python3 \
        python3-pip \
        python3-devel \
        python3-virtualenv \
        python3-rpm-macros \
        && dnf clean all

# Common CLI utilities useful during development and debugging
RUN dnf install -y \
        bash-completion \
        curl \
        wget \
        jq \
        tree \
        file \
        less \
        diffutils \
        patch \
        unzip \
        zip \
        tar \
        && dnf clean all

# ── Non-root user ─────────────────────────────────────────────────────────────
# Podman rootless: the container UID 1000 maps to your real host UID.
# If your host UID differs, VSCode Dev Containers handles the remapping via
# the "updateRemoteUserUID" feature in devcontainer.json.
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --shell /bin/bash \
               --create-home $USERNAME

# Allow devuser to use pip without --user flag inside the container
RUN mkdir -p /usr/local/lib/python3 \
    && chown -R $USERNAME:$USERNAME /usr/local/lib

# ── Python dev tools ──────────────────────────────────────────────────────────
# Install as root into the system Python so they are available on PATH
# without activating a venv (convenient for make targets).
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements-dev.txt

# ── VSCode server directory ──────────────────────────────────────────────────
# The Dev Containers extension mounts a named volume at /vscode and installs
# its server there. With --cap-drop=ALL the volume is created root-owned and
# devuser can't write to it. Pre-creating it here and chowning it ensures
# devuser owns the mount point so the server install succeeds.
RUN mkdir -p /vscode && chown $USERNAME:$USERNAME /vscode

# ── Shell environment ─────────────────────────────────────────────────────────
# Persist shell history across container rebuilds by storing it in the
# workspace volume (mounted at /workspace).
USER $USERNAME
RUN echo 'export HISTFILE=/workspace/.devcontainer/.bash_history' >> ~/.bashrc \
    && echo 'export PYTHONDONTWRITEBYTECODE=1' >> ~/.bashrc \
    && echo 'export PYTHONUNBUFFERED=1' >> ~/.bashrc \
    && echo 'export PYTHONPATH=/workspace/src' >> ~/.bashrc

WORKDIR /workspace
