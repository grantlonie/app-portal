# App Portal

Static directory of personal apps at `apps.grantlonie.com`.

## Stack

- Static HTML / CSS / JS served by `nginx:alpine`
- App catalog in [`public/apps.json`](public/apps.json)
- Joins the external Docker network `personal-infra-shared`

## Local preview

```bash
python3 -m http.server --directory public 8080
```

Open http://localhost:8080

## Deploy

One-time VPS setup (see personal-infra `docs/app-deploy.md`):

1. DNS `A` record: `apps.grantlonie.com` → VPS IP
2. Caddy route in personal-infra:

```caddyfile
apps.grantlonie.com {
	reverse_proxy apps:80
}
```

3. Clone and start:

```bash
sudo -u deploy git clone git@github.com:grantlonie/app-portal.git /srv/apps/app-portal
cd /srv/apps/app-portal
docker compose up -d
```

Day-to-day: push to `main` (GitHub Actions) or run `./deploy.sh`.

## Adding an app

1. Add a Caddy block (and DNS) in personal-infra.
2. Append an entry to `public/apps.json` (name, url, description, icon).
3. Optionally add an SVG under `public/icons/`.
