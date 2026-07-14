# South Kesteven one-shot live canary

The remediation plan already authorizes exactly one run of this canary after the
offline acceptance suite passes. No additional approval is needed for that one
run. It is not called by pytest, Make, CI, the release workflow, or the disposable
Home Assistant suite, and it must not run before the offline gate passes. A retry,
second lookup, changed fixture, or expanded destination is outside that approval.

The runner reads only the committed `SouthKestevenDistrictCouncil` values from
`uk_bin_collection/tests/input.json`. It has no postcode, house number, URL, or
WebDriver command-line override. A fixed environment acknowledgement, a fixed
command acknowledgement, a five-second start delay, an exclusive one-shot lock,
and the proxy's paced 256-connection ceiling prevent accidental repeated runs.
The ceiling allows one browser page flow to load its assets; it does not authorize
more than the runner's single logical address lookup.

## Network boundary

Create two new, run-ID-scoped rootless Podman networks:

- `ukbcd-canary-internal-<run-id>` is an `--internal` network. Only the runner,
  Selenium, and proxy join it. Runner and Selenium have no other network.
- `ukbcd-canary-egress-<run-id>` is joined only by the proxy. The proxy accepts
  only exact `www.southkesteven.gov.uk` and
  `selfservice.southkesteven.gov.uk` destinations on ports 80 and 443.

The allowlist proxy never logs a request path, query, header, payload, postcode,
house number, or denied hostname. Its complete log vocabulary is an allowlisted
host (or the constant `[DENIED]`) and a proxy status code. Redirects to any other
origin fail at the next proxy request. The proxy has a read-only filesystem,
drops every capability, has no mounts, and is the only process with an egress
route.

Chrome must receive both of these Selenium image environment values:

```text
SE_BROWSER_ARGS_UKBCD_PROXY=--proxy-server=http://ukbcd-live-proxy:3128
SE_BROWSER_ARGS_UKBCD_NO_BYPASS=--proxy-bypass-list=<-loopback>
```

Chromium normally bypasses proxies for loopback. The special `<-loopback>` token
removes that implicit bypass and adds no replacement bypass host. Background
networking, sync, and default apps are disabled as additional noise controls.

## Reviewed orchestration shape

The following is a reference sequence, not an executable script. Substitute the
already-recorded digest-pinned candidate and Selenium image names. Build/pull
images only during the plan's preparation window. Never substitute mutable tags
in the evidence run.

```bash
set -eu
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
INTERNAL="ukbcd-canary-internal-${RUN_ID}"
EGRESS="ukbcd-canary-egress-${RUN_ID}"
PROXY="ukbcd-live-proxy-${RUN_ID}"
SELENIUM="ukbcd-live-selenium-${RUN_ID}"
RUNNER="ukbcd-live-runner-${RUN_ID}"
PROXY_IMAGE_REF="LOCAL_LIVE_PROXY_IMAGE@sha256:RECORD_BEFORE_RUN"
SELENIUM_IMAGE_REF="PINNED_SELENIUM_IMAGE@sha256:RECORD_BEFORE_RUN"
RUNNER_IMAGE_REF="LOCAL_LIVE_CANARY_IMAGE@sha256:RECORD_BEFORE_RUN"

# Record the full local immutable image IDs which container inspect will expose.
PROXY_IMAGE_ID="$(podman image inspect --format '{{.Id}}' "$PROXY_IMAGE_REF")"
SELENIUM_IMAGE_ID="$(podman image inspect --format '{{.Id}}' "$SELENIUM_IMAGE_REF")"
RUNNER_IMAGE_ID="$(podman image inspect --format '{{.Id}}' "$RUNNER_IMAGE_REF")"

podman network create --internal "$INTERNAL"
podman network create "$EGRESS"

podman create --name "$PROXY" \
  --network "$INTERNAL:alias=ukbcd-live-proxy" \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=64 --cpus=0.25 --memory=192m \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
  "$PROXY_IMAGE_ID"
podman network connect "$EGRESS" "$PROXY"

podman create --name "$SELENIUM" \
  --network "$INTERNAL:alias=selenium" \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=512 --cpus=3 --memory=3500m --shm-size=2g \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m \
  --tmpfs /home/seluser:rw,nosuid,nodev,size=512m \
  -e SE_BROWSER_ARGS_UKBCD_PROXY=--proxy-server=http://ukbcd-live-proxy:3128 \
  -e 'SE_BROWSER_ARGS_UKBCD_NO_BYPASS=--proxy-bypass-list=<-loopback>' \
  -e SE_BROWSER_ARGS_UKBCD_BACKGROUND=--disable-background-networking \
  -e SE_BROWSER_ARGS_UKBCD_SYNC=--disable-sync \
  -e SE_BROWSER_ARGS_UKBCD_DEFAULT_APPS=--disable-default-apps \
  -e SE_NODE_MAX_SESSIONS=1 -e SE_NODE_OVERRIDE_MAX_SESSIONS=false \
  -e SE_OFFLINE=true -e SE_ENABLE_TRACING=false \
  "$SELENIUM_IMAGE_ID"

podman create --name "$RUNNER" \
  --network "$INTERNAL" \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=96 --cpus=0.5 --memory=512m \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=32m \
  -e UKBCD_LIVE_CANARY_APPROVED=one-public-fixture-lookup \
  "$RUNNER_IMAGE_ID"

python tests/disposable_ha/live_canary_safety_check.py \
  --internal-network "$INTERNAL" --egress-network "$EGRESS" \
  --proxy "$PROXY" --selenium "$SELENIUM" --runner "$RUNNER" \
  --expected-proxy-image "$PROXY_IMAGE_ID" \
  --expected-selenium-image "$SELENIUM_IMAGE_ID" \
  --expected-runner-image "$RUNNER_IMAGE_ID" \
  --output "live-canary-safety-${RUN_ID}.json"
```

The safety check must pass while all three application containers are still in
`created` state. It fails if Podman is not rootless; either application container
has egress; the proxy lacks either network; any host port, mount, device, socket,
added capability, writable root, restart policy, or missing resource limit is
found; Chrome has a bypass; or the total limits exceed 6 CPUs/7 GiB. Membership
comes from the two network-inspect results and must be exact. Capability removal
must be present as `--cap-drop all` in each inspected create command and as the
complete expected drop set in container state; a merely non-empty drop list does
not pass. The full local image IDs must match the three separately recorded
immutable values; mutable image names and short IDs do not pass. Host PID, IPC,
user, UTS, or cgroup namespace modes do not pass where the runtime exposes them.

After that check passes, start the proxy and Selenium, wait only for Selenium's
internal `/status` endpoint, and attach to the runner once. Do not use `podman
run`, because that would bypass the inspected `created` containers. Export only:

- the pre-start safety JSON;
- the runner's one-line JSON summary;
- the proxy's safe host/status log;
- image digests and the candidate wheel/local commit hashes.

Do not export Selenium logs, browser profiles, page source, screenshots, `/tmp`,
or any container filesystem. The runner suppresses collector stdout/stderr and
prints only a bin-row count or a short redacted error. Review exported text with
the same postcode/number/URL redactor before moving it to Windows.

Remove only the exact three container and two network names after evidence is
safe. Never use a global prune. A failed safety check is terminal for that run;
do not add host networking, a host port, a bind mount, privilege, or a socket to
make the canary pass.
