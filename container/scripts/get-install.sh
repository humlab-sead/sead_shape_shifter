#!/bin/bash

check_podman_prerequisites() {
    local failed=0

    echo "Checking Podman setup..."

    # Podman installed
    if command -v podman >/dev/null 2>&1; then
        echo "OK: podman installed ($(podman --version))"
    else
        echo "FAIL: podman is not installed"
        failed=1
    fi

    # podman-compose installed
    if command -v podman-compose >/dev/null 2>&1; then
        echo "OK: podman-compose installed ($(podman-compose --version 2>/dev/null | head -n1))"
    else
        echo "FAIL: podman-compose is not installed"
        failed=1
    fi

    # systemd lingering enabled
    if [[ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" == "yes" ]]; then
        echo "OK: lingering enabled for $USER"
    else
        echo "FAIL: lingering not enabled for $USER"
        failed=1
    fi

    # Rootless Podman user namespace works
    if podman unshare id >/dev/null 2>&1; then
        echo "OK: podman rootless user namespace works"
    else
        echo "FAIL: 'podman unshare id' failed"
        failed=1
    fi

    if (( failed )); then
      echo "Podman setup is incomplete."
      echo "Podman prerequisites are missing"
      exit 1
    fi

    echo "Podman setup is complete."
    return 0
}

check_podman_prerequisites

# REFS=security-regression-and-release-verification

# curl -L https://github.com/humlab-sead/sead_shape_shifter/archive/refs/heads/$REFS.tar.gz |
#   tar -xz \
#     --wildcards \
#     --strip-components=1 \
#     "sead_shape_shifter-$REFS/container/*"
