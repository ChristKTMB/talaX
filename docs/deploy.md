# Deploying the Tala X web service

The site and its API run in Docker (`compose.yaml`): an `api` container and an
`nginx` container that serves the Angular front, applies the security policy
and the limits, and passes `/api` on. On the server, the server's own nginx
terminates HTTPS in front of it, with a certificate from certbot:

```
Internet ──HTTPS──▶ nginx of the server (certbot)    HTTPS only
                         │ http://127.0.0.1:9188
                         ▼
                    nginx container                  site, security policy, limits
                         │
                         ▼
                    api container                    analysis
```

Nothing is kept: no file, no result, no log line with an address or a file
name. There is nothing to back up beyond this repository and the `.env` file.

## What the server needs

- A Linux server in the European Union (the privacy policy names the host).
- Docker Engine with the Compose plugin: `docker compose version`.
- git, nginx and certbot with its nginx plugin (`python3-certbot-nginx`).
- DNS: `A` (and `AAAA` if the server has IPv6) records for `talax.online` and
  `www.talax.online`, pointing to the server. Check with
  `dig +short talax.online` before asking for a certificate.
- Ports 80 and 443 open in the firewall.

Keep any other administration tool of the server (Jenkins, for example) out of
public reach: this server receives people's photos.

## First installation

### 1. Get the code

```sh
sudo mkdir -p /opt/talax && sudo chown "$USER" /opt/talax
git clone https://github.com/ChristKTMB/talaX.git /opt/talax
cd /opt/talax
```

### 2. Choose the local port

The containers listen on `127.0.0.1:9188` by default. If another application
of the server already uses it (`ss -ltn | grep 9188`), choose another one:

```sh
echo "TALAX_PORT=9288" > .env      # example: any free port
```

Then use that port in every command below and in `proxy_pass` (step 4).

### 3. Start the service

```sh
docker compose up --build --detach --wait
curl -fsS http://127.0.0.1:9188/api/health
```

The answer gives the versions of Tala X and ExifTool. The first build takes a
few minutes.

### 4. Configure the server's nginx

```sh
sudo cp deploy/host-nginx.conf /etc/nginx/sites-available/talax.online
sudo ln -s /etc/nginx/sites-available/talax.online /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

If you changed `TALAX_PORT`, change `proxy_pass` in the copied file to match.
Only this site is added: the other sites of the server are not touched.

### 5. HTTPS

```sh
sudo certbot --nginx -d talax.online -d www.talax.online --redirect --hsts
sudo nginx -t && sudo systemctl reload nginx
```

certbot adds the certificate to the `talax.online` site and sends HTTP
visitors to HTTPS. Renewal is automatic (`systemctl list-timers | grep certbot`).

### 6. Check

```sh
curl -sI https://talax.online | grep -iE 'HTTP/|content-security-policy|referrer-policy'
curl -fsS https://talax.online/api/health
```

Then, in a browser: open https://talax.online, analyse a photo with no
sensitive position, answer the sky question, show the map, download the
report, switch FR / EN, open both legal pages.

Then check that the promises of the privacy policy hold on the server:

```sh
# No file left behind.
docker compose exec -T api sh -c 'ls -A /tmp | wc -l'      # 0
# No visitor address in the containers' logs.
docker compose logs | grep -E '([0-9]{1,3}\.){3}[0-9]{1,3}' | grep -v 0.0.0.0
# No access log for the site (the file must not exist or stay empty).
sudo ls -la /var/log/nginx/ | grep talax
```

## Updating

```sh
cd /opt/talax
git pull
docker compose up --build --detach --wait
docker image prune --force
```

If `deploy/host-nginx.conf` changed, compare it with
`/etc/nginx/sites-available/talax.online` (which holds certbot's lines too)
and report the change by hand.

Before each release of the library, refresh the C2PA trust list
(`uv run python scripts/update_c2pa_trust.py`).

## Useful commands

```sh
docker compose ps                     # state of the containers
docker compose logs --tail 50 api     # last lines of the API (no address, no file name)
docker compose restart                # restart both containers
docker compose down                   # stop the service
```
