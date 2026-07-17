# claude-pod image — Ubuntu 26.04 + Amazon Corretto 25 + Node 24 + current Go + Claude Code.
#
# Toolchains are stable layers (cached ~forever). Claude is the LAST layer, so
# `claude-pod --update-claude` rebuilds only it (seconds) while the toolchains stay
# cached. The auto-updater is disabled: the baked version is authoritative.
FROM ubuntu:26.04
ARG DEBIAN_FRONTEND=noninteractive

# ── base dev tools ──
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl wget ca-certificates gnupg build-essential \
      ripgrep jq less unzip zip xz-utils procps openssh-client ncurses-term \
      shellcheck shfmt nftables \
      python3 python3-pip python3-venv tzdata \
 && rm -rf /var/lib/apt/lists/*

# ── python maintainer toolchain (pinned) ──
# The pod denies egress at runtime (ADR 2026-07-17), so the strict battery's
# python tools bake in at build time. ruff must equal pyproject.toml's
# required-version — ruff refuses a mismatch; check-sync's pod-toolchain-pins
# step gates all three pins. Bump together via deps-upgrade.
RUN python3 -m venv /opt/pytools \
 && /opt/pytools/bin/pip install --no-cache-dir \
      'ruff==0.15.22' 'mypy==2.3.0' 'bandit==1.9.4' \
 && ln -s /opt/pytools/bin/ruff /opt/pytools/bin/mypy /opt/pytools/bin/bandit \
      /usr/local/bin/

# ── Amazon Corretto 25 (JDK) ──
RUN curl -fsSL https://apt.corretto.aws/corretto.key \
      | gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" \
      > /etc/apt/sources.list.d/corretto.list \
 && apt-get update && apt-get install -y java-25-amazon-corretto-jdk \
 && rm -rf /var/lib/apt/lists/*

# ── Node 24 (official nodejs.org distribution) ──
RUN set -eux; \
    narch="$(dpkg --print-architecture)"; case "$narch" in amd64) narch=x64;; esac; \
    file="$(curl -fsSL https://nodejs.org/dist/latest-v24.x/ \
            | grep -oE "node-v24\.[0-9]+\.[0-9]+-linux-${narch}\.tar\.xz" | head -1)"; \
    test -n "$file"; \
    curl -fsSL "https://nodejs.org/dist/latest-v24.x/${file}" \
      | tar -C /usr/local --strip-components=1 -xJ

# ── current Go (resolved at build time, arch-aware) ──
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64) goarch=amd64;; arm64) goarch=arm64;; *) goarch="$arch";; esac; \
    ver="$(curl -fsSL 'https://go.dev/VERSION?m=text' | head -1)"; \
    curl -fsSL "https://go.dev/dl/${ver}.linux-${goarch}.tar.gz" | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:${PATH}"

# ── non-root dev home (agent runs as your uid at runtime) ──
RUN mkdir -p /home/dev && chmod 777 /home/dev
ENV HOME=/home/dev

# ── Claude Code — LAST layer; baked, auto-updater off (use `claude-pod --update-claude`) ──
ENV DISABLE_AUTOUPDATER=1
ARG CLAUDE_VERSION=latest
ARG CLAUDE_CACHE_BUST=0
RUN set -eux; \
    echo "claude cache-bust: ${CLAUDE_CACHE_BUST}"; \
    export CLAUDE_HOME=/opt/claude; mkdir -p "$CLAUDE_HOME"; \
    if [ "${CLAUDE_VERSION}" = "latest" ]; then \
      HOME="$CLAUDE_HOME" bash -c 'curl -fsSL https://claude.ai/install.sh | bash'; \
    else \
      HOME="$CLAUDE_HOME" bash -c "curl -fsSL https://claude.ai/install.sh | bash -s -- ${CLAUDE_VERSION}"; \
    fi; \
    chmod -R a+rX "$CLAUDE_HOME"; \
    ls -l "$CLAUDE_HOME/.local/bin"
ENV PATH="/opt/claude/.local/bin:${PATH}"
