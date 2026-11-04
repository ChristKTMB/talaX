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
npm run e2e             # end-to-end tests in Chromium, against `docker compose up`
```

The end-to-end tests need the browser once: `npx playwright install chromium`.
They use a synthetic photo (`e2e/fixtures/paris.jpg`: a plain colour, a made-up
camera, a date and a position in Paris), never a photo of the corpus.

`scripts/sync-docs.mjs` copies the logo and favicons from `../docs/brand`, and
turns the terms of use and privacy policy of `../docs/legal` into HTML, before
every build, dev server and test run: `docs/` stays the only source.

The whole service, as deployed, from the repository root:
`docker compose up --build`, then http://127.0.0.1:8088.
