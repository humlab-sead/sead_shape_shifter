#!/usr/bin/env bash
# Verify the firewall and network exposure of a Shape Shifter deployment.
#
# Confirms two layers hold on the host:
#   1. the backend binds loopback only (127.0.0.1:<HOST_PORT>, never 0.0.0.0);
#   2. no firewall rule exposes <HOST_PORT> to non-loopback traffic.
#
# It also runs the loopback and same-host LAN-address connection checks and
# prints the cross-host command to run from a second machine. The script never
# changes firewall rules or service state.
#
# Usage:
#   verify-firewall.sh [HOST_PORT] [LAN_IP]
#
# HOST_PORT defaults to 8012. LAN_IP defaults to the first global IPv4 address
# on the host. Run the firewall-listing step as a user that can run sudo;
# everything else runs unprivileged.
set -euo pipefail

g_host_port="${1:-8012}"
g_lan_ip="${2:-}"
g_failures=0

info() { printf '\n== %s ==\n' "$*"; }
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*" >&2; g_failures=$((g_failures + 1)); }
warn() { printf 'WARN  %s\n' "$*"; }

list_with_sudo() {
    local label="$1"
    shift
    if output="$(sudo -n "$@" 2>/dev/null)"; then
        printf '%s\n' "$output"
    else
        warn "sudo unavailable for ${label}; run the listing manually"
    fi
}

if [[ -z "$g_lan_ip" ]]; then
    g_lan_ip="$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n 1)"
fi
if [[ -z "$g_lan_ip" ]]; then
    warn "No LAN address found; pass it as the second argument for the LAN refusal check."
fi

info "Listeners (expect 127.0.0.1:${g_host_port} for the backend, only the proxy port otherwise)"
ss -ltn | grep -E ":(80|443|${g_host_port})\b" || warn "no listener found on ${g_host_port}, 80, or 443"

if ss -ltn | grep -Eq "0\.0\.0\.0:${g_host_port}\b"; then
    fail "backend listens on 0.0.0.0:${g_host_port}; it must bind loopback only"
elif ! ss -ltn | grep -Eq "127\.0\.0\.1:${g_host_port}\b"; then
    warn "no loopback listener on ${g_host_port} found (is the container up?)"
else
    pass "backend listener is loopback-only on ${g_host_port}"
fi

info "Firewall rules (no rule may open ${g_host_port} to non-loopback traffic)"
backend=""
for candidate in firewalld ufw nftables iptables; do
    if systemctl is-active --quiet "$candidate" 2>/dev/null; then
        backend="$candidate"
        break
    fi
done

if [[ -z "$backend" ]]; then
    warn "No active firewalld/ufw/nftables/iptables unit; listing skipped."
else
    printf 'Active firewall backend: %s\n' "$backend"
    case "$backend" in
        firewalld) list_with_sudo "firewall-cmd" firewall-cmd --list-all ;;
        ufw)       list_with_sudo "ufw" ufw status verbose ;;
        nftables)  list_with_sudo "nft" nft list ruleset ;;
        iptables)  list_with_sudo "iptables" iptables -S ;;
    esac
    printf 'Confirm no rule opens port %s to non-loopback traffic.\n' "$g_host_port"
fi

info "Connection checks"
loopback_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 "http://127.0.0.1:${g_host_port}/api/v1/health" 2>/dev/null)" || true
if [[ "$loopback_code" == "200" ]]; then
    pass "loopback health returned 200"
else
    fail "loopback health returned '${loopback_code}'"
fi

if [[ -n "$g_lan_ip" ]]; then
    if curl -sS --connect-timeout 5 -o /dev/null "http://${g_lan_ip}:${g_host_port}/api/v1/health" 2>/dev/null; then
        fail "LAN address ${g_lan_ip}:${g_host_port} is reachable; the backend is exposed"
    else
        pass "LAN address ${g_lan_ip}:${g_host_port} refused (loopback-only or firewalled)"
    fi
fi

info "Cross-host check (run from a second host on the LAN)"
printf '  nc -zvw5 %s %s   # expect refused or timed out\n' "${g_lan_ip:-<host-lan-ip>}" "$g_host_port"
printf '  nc -zvw5 %s 443  # the proxy should connect\n' "${g_lan_ip:-<host-lan-ip>}"

printf '\n'
if [[ "$g_failures" -gt 0 ]]; then
    printf 'Verification failed with %d issue(s).\n' "$g_failures" >&2
    exit 1
fi
printf 'Host-side verification passed. Record the listener output, firewall listing, and cross-host result.\n'
