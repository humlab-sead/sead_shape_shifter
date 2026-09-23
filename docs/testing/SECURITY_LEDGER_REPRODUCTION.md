# Security Ledger Reproduction — Disposable Environment

How to run the September 2026 security findings ledger's test package without touching the host.

> **Read this before running anything.** The ledger's deployment-script and bootstrap tests run as
> root and reach real host paths. Do not run them on a workstation. Run them only in a disposable
> container or VM described below. See [Why isolation is required](#why-isolation-is-required).

**Audience:** maintainers and reviewers reproducing a ledger finding during remediation (Security
Hardening Follow-up, phases 2, 6, 7). This is not a CI procedure — the package is not a CI asset and
no workflow runs it.

**Scope:** running the operator-supplied ledger package in an isolated environment and confirming the
host was not modified. It does not restate the findings; those live in the ledger itself.

---

## What the package is

The ledger is a local, untracked findings report (`secrets/FINDINGS.md`) with a companion test
package. Each finding has a test that fails on the vulnerable code and passes once the defect is
closed. The package is **not** committed to this repository and is **not** a CI asset.

- The ledger report and its test package live outside version control, under a local `secrets/`
  directory that `.gitignore` excludes.
- The package entry point is a script referred to here as `RUN.sh`. It copies the tests into your
  checkout, runs them against that tree, and prints a cleanup command.
- The exact location of the package is operator-supplied and is written as `TBD` throughout this
  document. Replace `TBD` with the path to your local copy of the package before running.

Nothing from `secrets/` is committed by this or any remediation change. This document only describes
how to run the package; it does not copy the package or its findings.

---

## Why isolation is required

The ledger documents its own limits in its "Known limits" section (section 6). The relevant facts for
running it safely:

- **Root execution.** The bootstrap and deployment-script tests run as root with `DEPLOY_USER` set to
  the lowest-uid account. They exercise the real shipped scripts inside a sandbox with a stubbed
  `PATH`.
- **Containment is by practice, not by construction.** The package's stub wrappers rewrite *positional
  arguments only*. A shell redirection (`>`), `sed -i`, `cp --target-directory=`, or `bash -c` inside a
  shipped script reaches the real host. Several common tools in the harness (`cat`, `sed`, `grep`,
  `awk`, `stat`, `cut`, `bash`, `sh`, `env`, `readlink`, and others) are the **real binaries**, so a
  `sed -i` in a scripted path is not read-only.
- **The host snapshot is partial.** The after-the-fact check covers a fixed set of roots and does not
  see everything done after `sudo`. The package's own notes record that a probe writing a real host
  file still went green, which is why a VM is required rather than optional.
- **Do not forward the `sudo` stub.** With the shipped `TARGET_PATH` override, forwarding `sudo` makes
  the run issue real `podman exec … grant-application-role` calls against a real store.

Treat a green result as "this named defect is closed", not as a security pass. The package is not a
security suite.

---

## Prerequisites

- A disposable Linux container or VM you can destroy afterwards. Prefer a throwaway image with no
  secrets, no SSH agent, and no mounted host directories other than the ones you add on purpose.
- `podman` and `podman-compose` (the repository's container tooling), or a VM you control.
- A checkout of this repository at the commit under test.
- The operator-supplied ledger package, including its `RUN.sh`. Path is `TBD`.
- A Python environment for the repository (the repo's `.venv/`), created inside the disposable
  environment, not inherited from the host.

---

## Run recipe

Run every step inside the disposable environment. Do not reuse a host shell.

### 1. Start a disposable environment

Option A — throwaway container (rootless podman, no host mounts except the checkout):

```bash
# From the disposable host, not your workstation.
# Mount only the repo checkout; do not mount $HOME, /etc, or secrets.
podman run --rm -it \
  --name ledger-repro \
  -v "$PWD:/work:ro" \
  docker.io/library/python:3.12-slim bash
```

Option B — disposable VM: boot a fresh VM, install `git`, `podman`, and a Python 3.12+ interpreter,
then clone the repository into it. Destroy the VM afterwards.

### 2. Prepare the checkout inside the environment

```bash
cd /work
git checkout <commit-under-test>
python -m venv .venv
.venv/bin/pip install -e ".[api]"   # or: make install
```

### 3. Copy in the ledger package

Copy the operator-supplied package into the disposable environment from a location that is not the
host you are protecting. Set the package path:

```bash
LEDGER_PKG="TBD"   # path to the local ledger package inside this environment
```

### 4. Run the package against the checkout

```bash
# Run from inside the checkout. Extra arguments go to pytest, not to a git ref.
"$LEDGER_PKG/RUN.sh"
```

The script prints a cleanup command when it finishes. Run that cleanup command before discarding the
environment.

To run a single finding's test, pass its node id through to pytest as documented by the package.

### 5. Confirm the host is untouched

The package asserts, per layout run, that a fixed set of host paths is unchanged by mode, owner, and
modification time, and that `$HOME`'s top-level entry names are unchanged. The checked roots are:

- `/etc/nginx`
- `/etc/systemd/system`
- `/data`
- `config`, `container`, and `container-data` under `$HOME`

`$HOME` is not walked wholesale on purpose: shell history, editor state, and agent journals change
there constantly and would read as false alarms.

If the run reports it "left entries behind in the real home directory" or flags a changed root, the
isolation failed — discard the environment and investigate before trusting any result. Because the
snapshot is partial (see [Why isolation is required](#why-isolation-is-required)), a clean report is
necessary but not sufficient; still run inside a disposable environment.

### 6. Discard the environment

```bash
# Option A
podman rm -f ledger-repro 2>/dev/null || true
# Option B: destroy the VM.
```

Do not carry the disposable environment's state back to any persistent host.

---

## Host-untouched assertion (manual check)

Independently of the package's own snapshot, capture the host state before and after and compare. Run
these inside the disposable environment before step 4 and again after step 5:

```bash
# Before the run (step 4) and after (step 5). Compare the two outputs.
{
  stat -c '%n %a %U:%G %Y' /etc/nginx /etc/systemd/system /data 2>/dev/null
  find "$HOME" -maxdepth 1 -mindepth 1 -printf '%P\n' 2>/dev/null | sort
} | tee ledger-host-state-$(date +%s).txt
```

The two captures must match. Any difference means the run reached the host.

---

## Constraints

- Do not commit anything from `secrets/`. The package, its report, and its fixtures stay untracked.
- The package path is operator-supplied and written as `TBD` here. Do not hard-code a personal path
  into any committed file.
- Never run the root-only bootstrap or deployment-script tests on a workstation.
- Do not make the `sudo` stub forward to real `sudo`.

## Related

- Security Hardening Follow-up proposal and phase plan:
  [../proposals/SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md](../proposals/SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md)
- Testing strategy and commands: [../TESTING.md](../TESTING.md)
- Container build and run: [../../container/README.md](../../container/README.md)
