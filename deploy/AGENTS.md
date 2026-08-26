# AGENTS.md — Deploy

Kubernetes manifests for the Palworld gameserver, reconciled by ArgoCD.

```
application.yaml           ArgoCD application
manifests/gameserver.yaml  Agones GameServer
manifests/*-sealed-secret.yaml   encrypted credentials
manifests/live-*.yaml      service + HTTPRoute for the relay's /live API
manifests/*-pvc.yaml       saves and backups volumes
seal-credentials.sh        re-seal server credentials
seal-rcon.sh               re-seal RCON credentials
```

## Rules

**The sealed secrets are safe to commit; plain Secrets are not.** A
`SealedSecret` holds ciphertext only the cluster's controller can decrypt,
which is why these live in a public repo. Never commit a `kind: Secret`
with real data, and never paste a decrypted value into a manifest.

**Re-seal with the scripts.** `seal-rcon.sh` and `seal-credentials.sh`
read passwords from the environment and write the sealed manifests. They
require `kubeseal` and access to the cluster's controller.

**`live-httproute.yaml` publishes the relay**, which is what the map and
the Discord bot call. Changing the host or path breaks both.
