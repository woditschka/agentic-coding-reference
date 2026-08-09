# claude-dev image — Debian 13 slim + Amazon Corretto 25 + Node 24 + current Go + Claude Code.
#
# Layer order: base setup (system tools, egress runtime, non-root
# account), then dev toolchains, then Claude LAST. `claude-dev update`
# rebuilds only the Claude layer (seconds); everything above stays cached.
# The auto-updater is disabled: the baked version is authoritative.
#
# Supply chain (ADR 2026-07-20-pod-image-supply-chain): Claude Code installs
# from Anthropic's GPG-signed apt repo, key fingerprint pinned below — no
# piped-to-shell installer, and a battery tripwire fails the idiom returning.
# Debian and Corretto packages are apt-signature-verified. Node and Go ride
# TLS alone, resolved to latest at build time; `claude-dev update --all`
# refreshes them. The base choice and the no-pins trade live in the ADR.
FROM debian:13-slim
ARG DEBIAN_FRONTEND=noninteractive

# ══ base setup ══

# ── base dev tools ──
# `upgrade` first: base-image packages (libc, libssl, apt, …) get Debian's
# security fixes at build time, not only when `update --all` re-pulls the base.
RUN apt-get update && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends \
      git curl wget ca-certificates gnupg build-essential \
      ripgrep jq less unzip zip xz-utils procps openssh-client ncurses-term \
      shellcheck shfmt \
      python3 python3-pip python3-venv tzdata \
 && rm -rf /var/lib/apt/lists/*

# ── confinement runtime — security controls, NOT dev tools ──
# squid is the session's only path to the internet (ADR 2026-07-29); socat
# carries the --ide loopback tunnel through squid's CONNECT. The battery's
# toolchain-pins step asserts both stay — never remove in a dev-tool cleanup.
# bubblewrap ships but is NOT used by default: under Docker's default seccomp
# profile it cannot create a user namespace (measured 2026-07-29; README §
# Process has the matrix), so the launcher forces Claude's in-process sandbox
# off. Kept (~50KB) so the other posture needs no rebuild on a permissive engine.
RUN apt-get update && apt-get install -y --no-install-recommends \
      squid socat bubblewrap \
 && rm -rf /var/lib/apt/lists/*

# ── non-root dev home (the wrapper overrides both at runtime: --user <host uid>, -e HOME) ──
# uid 1000: Debian ships no default user, so the conventional first uid is free.
RUN useradd --uid 1000 --user-group --home-dir /home/dev --no-create-home dev \
 && mkdir -p /home/dev && chown dev:dev /home/dev && chmod 755 /home/dev
ENV HOME=/home/dev

# ══ dev toolchains ══

# ── python maintainer toolchain (pinned) ──
# Egress is default-denied at runtime (ADR 2026-07-29), so the strict
# battery's python tools bake in at build time. ruff must equal pyproject's
# required-version; verify-harness's toolchain-pins step gates all three pins.
RUN python3 -m venv /opt/pytools \
 && /opt/pytools/bin/pip install --no-cache-dir \
      'ruff==0.15.22' 'mypy==2.3.0' 'bandit==1.9.4' \
 && ln -s /opt/pytools/bin/ruff /opt/pytools/bin/mypy /opt/pytools/bin/bandit \
      /usr/local/bin/

# ── Amazon Corretto 25 (JDK) ──
# Scratch GNUPGHOME: gpg would otherwise bake a root-owned .gnupg into
# /home/dev, breaking gpg for direct runs.
RUN set -eux; \
    GNUPGHOME="$(mktemp -d)"; export GNUPGHOME; \
    curl -fsSL https://apt.corretto.aws/corretto.key \
      | gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg; \
    rm -rf "$GNUPGHOME"; \
    echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" \
      > /etc/apt/sources.list.d/corretto.list; \
    apt-get update && apt-get install -y java-25-amazon-corretto-jdk; \
    rm -rf /var/lib/apt/lists/*

# ── Node 24 (official nodejs.org distribution) ──
RUN set -eux; \
    narch="$(dpkg --print-architecture)"; case "$narch" in amd64) narch=x64;; esac; \
    file="$(curl -fsSL https://nodejs.org/dist/latest-v24.x/ \
            | grep -oE "node-v24\.[0-9]+\.[0-9]+-linux-${narch}\.tar\.xz" | head -1)"; \
    test -n "$file"; \
    curl -fsSL "https://nodejs.org/dist/latest-v24.x/${file}" \
      | tar -C /usr/local --strip-components=1 -xJ; \
    chown -R root:root /usr/local/bin /usr/local/lib /usr/local/include /usr/local/share  # tarball carries a build uid; PATH dirs stay root-owned

# ── current Go (resolved at build time, arch-aware) ──
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64) goarch=amd64;; arm64) goarch=arm64;; *) goarch="$arch";; esac; \
    ver="$(curl -fsSL 'https://go.dev/VERSION?m=text' | head -1)"; \
    curl -fsSL "https://go.dev/dl/${ver}.linux-${goarch}.tar.gz" | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:${PATH}"

# ══ Claude Code — LAST layer ══

# Anthropic's signed apt repo, auto-updater off (use `claude-dev update`).
# Before apt trusts the downloaded key, the layer asserts it holds exactly one
# key whose fingerprint equals the pin below — the value documented at
# code.claude.com/docs/en/setup. A bare x.y.z CLAUDE_VERSION maps to deb
# revision x.y.z-1; the repo serves a rolling window (~80 releases, 2026-07-20).
# GPG_FPR, not KEY_FPR: a *KEY* name trips BuildKit's SecretsUsedInArgOrEnv
# lint, and a file-wide skip would blind it to a real secret landing later.
# The fingerprint itself is public data.
ENV DISABLE_AUTOUPDATER=1
ARG CLAUDE_GPG_FPR=31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE
ARG CLAUDE_VERSION=latest
ARG CLAUDE_CACHE_BUST=0
RUN set -eux; \
    echo "claude cache-bust: ${CLAUDE_CACHE_BUST}"; \
    GNUPGHOME="$(mktemp -d)"; export GNUPGHOME; \
    curl -fsSL https://downloads.claude.ai/keys/claude-code.asc -o /tmp/claude-code.asc; \
    gpg --show-keys --with-colons /tmp/claude-code.asc > /tmp/keyinfo; \
    [ "$(grep -c '^pub:' /tmp/keyinfo)" = 1 ]; \
    awk -F: '$1=="fpr"{print $10; exit}' /tmp/keyinfo | grep -qix "${CLAUDE_GPG_FPR}"; \
    gpg --dearmor -o /usr/share/keyrings/claude-code.gpg /tmp/claude-code.asc; \
    rm -rf /tmp/claude-code.asc /tmp/keyinfo "$GNUPGHOME"; \
    echo "deb [signed-by=/usr/share/keyrings/claude-code.gpg] https://downloads.claude.ai/claude-code/apt/latest latest main" \
      > /etc/apt/sources.list.d/claude-code.list; \
    apt-get update; \
    if [ "${CLAUDE_VERSION}" = latest ]; then \
      apt-get install -y --no-install-recommends claude-code; \
    else \
      v="${CLAUDE_VERSION}"; case "$v" in *-*) ;; *) v="${v}-1";; esac; \
      apt-get install -y --no-install-recommends "claude-code=${v}"; \
    fi; \
    rm -rf /var/lib/apt/lists/*; \
    smoke="$(mktemp -d)"; HOME="$smoke" claude --version; rm -rf "$smoke"

# Non-root by default: a direct `docker run` of this image never lands on
# root. The wrapper still passes an explicit --user on every run, which
# overrides this.
USER dev
