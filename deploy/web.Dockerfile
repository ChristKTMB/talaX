# Tala X front: the Angular site, built here and served by nginx, which also
# passes /api on to the API container (deploy/nginx.conf). Node only runs at
# build time, never in production.

FROM node:24.22.2-alpine3.24 AS build
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
# The front reads the logo and the legal pages from docs/ at build time
# (web/scripts/sync-docs.mjs).
COPY docs/brand /src/docs/brand
COPY docs/legal /src/docs/legal
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30.6-alpine
USER root
RUN rm -rf /usr/share/nginx/html/*
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/web/dist/talax-web/browser /usr/share/nginx/html
USER nginx
