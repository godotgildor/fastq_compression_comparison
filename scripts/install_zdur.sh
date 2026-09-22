#!/bin/bash
# Install zDUR precompiled binary from GitHub releases.
#
# LICENSE: zDUR requires a non-commercial license key. Academic researchers
# can request a free 6-month license by contacting the zDUR team (see
# https://github.com/MGI-EU/zDUR). On the first run, zDUR will prompt you
# to enter your license key interactively; it is then stored locally and
# not required again.
#
# Usage: bash scripts/install_zdur.sh
set -euo pipefail

ZDUR_VERSION="1.0.0-beta"
INSTALL_DIR="/usr/local/bin"

# Detect platform
ARCH=$(uname -m)
OS=$(uname -s)

if [[ "$OS" == "Linux" ]]; then
    if [[ "$ARCH" == "x86_64" ]]; then
        BINARY="zDUR-x86-linux"
    elif [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
        BINARY="zDUR-arm-linux"
    else
        echo "Unsupported Linux architecture: $ARCH" >&2
        exit 1
    fi
elif [[ "$OS" == "Darwin" ]]; then
    if [[ "$ARCH" == "x86_64" ]]; then
        BINARY="zDUR-x86-mac"
    elif [[ "$ARCH" == "arm64" ]]; then
        BINARY="zDUR-arm-mac"
    else
        echo "Unsupported macOS architecture: $ARCH" >&2
        exit 1
    fi
else
    echo "Unsupported OS: $OS" >&2
    exit 1
fi

URL="https://github.com/MGI-EU/zDUR/releases/download/${ZDUR_VERSION}/${BINARY}"
echo "Downloading zDUR ${ZDUR_VERSION} (${BINARY})..."
curl -fsSL "$URL" -o "${INSTALL_DIR}/zdur"
chmod +x "${INSTALL_DIR}/zdur"
echo "zDUR installed to ${INSTALL_DIR}/zdur"
echo ""
echo "NOTE: On first use, zDUR will prompt for a license key."
echo "Request a free academic license at https://github.com/MGI-EU/zDUR"
