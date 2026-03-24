# Deployment

## Container Build

```bash
make podman-build
```

## Kubernetes

Add manifests to `deploy/kubernetes/` as needed.

## Systemd

Copy the binary to `/usr/local/bin/` and create a systemd unit file.
