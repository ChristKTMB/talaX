# Tala X web front

The Angular site of Tala X. It talks to the API on the same origin (`/api`)
and is served by nginx in production (`deploy/web.Dockerfile`).

```sh
nvm use                 # Node from .nvmrc
npm ci
npm start               # http://localhost:4200, /api passed to `talax serve` on port 8000
npm test                # unit tests (Vitest)
npm run lint
npm run format:check
npm run build
```

`scripts/sync-docs.mjs` copies the logo and favicons from `../docs/brand`
before every build, dev server and test run: `docs/` stays the only source.

The whole service, as deployed, from the repository root:
`docker compose up --build`, then http://127.0.0.1:8088.
