# AGENTS.md — Server

Container images and local compose for the Palworld gameserver.

```
Dockerfile          the gameserver image
Dockerfile.linux    linux variant
docker-compose.yml  local stack
e2e/rest.spec.ts    smoke tests against the game's REST API
```

## Rules

**No credentials in compose or Dockerfiles.** Passwords come from the
environment, and in the cluster from the sealed secrets in `deploy/`.

**`e2e/rest.spec.ts` needs a running server**, so it is not part of the
default CI run. Point it at a live instance deliberately.
