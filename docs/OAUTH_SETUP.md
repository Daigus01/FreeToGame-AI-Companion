# Configurar el login (Google + Discord) — D-11

El backend implementa el flujo OAuth 2.0 (authorization code). Solo se activan los proveedores cuyo **Client ID y Client Secret** estén en `.env`.
URIs de redirección que debes registrar (usa siempre `localhost`, no `127.0.0.1`: las cookies son por host):

| Proveedor | Redirect URI |
|---|---|
| Google | `http://localhost:8000/api/auth/google/callback` |
| Discord | `http://localhost:8000/api/auth/discord/callback` |

## 1. Google
1. https://console.cloud.google.com → crea/elige un proyecto.
2. *APIs & Services → OAuth consent screen*: tipo **External**, nombre de la app, tu correo. En modo *Testing* añade tu correo en **Test users** (solo ellos podrán entrar hasta publicar la app).
3. *Credentials → Create credentials → OAuth client ID → Web application*. En **Authorized redirect URIs** pega la URI de Google de la tabla.
4. Copia *Client ID* y *Client secret* a `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`. Scopes usados: `openid email profile`.

## 2. Discord
1. https://discord.com/developers/applications → **New Application**.
2. *OAuth2 → Redirects → Add Redirect*: pega la URI de Discord de la tabla y guarda.
3. En *OAuth2* copia **Client ID** y pulsa *Reset Secret* para obtener el **Client Secret**. Van a `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET`. Scopes usados: `identify email`.

## 3. `.env`
```
GOOGLE_CLIENT_ID=...        GOOGLE_CLIENT_SECRET=...
DISCORD_CLIENT_ID=...       DISCORD_CLIENT_SECRET=...
SESSION_SECRET=<aleatorio>  # genera uno:  docker compose exec backend python -c "import secrets;print(secrets.token_urlsafe(32))"
FRONTEND_URL=http://localhost:3000
BACKEND_PUBLIC_URL=http://localhost:8000
ALLOW_DEV_AUTH=false        # true solo si quieres seguir usando el header X-User-Id sin OAuth (desarrollo local)
```
Nunca subas `.env` a git (ya está en `.gitignore`).

## 4. Migración 003 en una base de datos ya creada
Docker solo ejecuta las migraciones la primera vez que se crea el volumen de Postgres. Si ya tenías datos, aplica la nueva (es idempotente):
```powershell
Get-Content backend\migrations\003_auth.sql | docker compose exec -T postgres psql -U ftg -d ftg
```
(En bash: `docker compose exec -T postgres psql -U ftg -d ftg < backend/migrations/003_auth.sql`.)

## 5. Reiniciar y probar
```powershell
docker compose up -d --force-recreate backend      # recarga las variables de .env
```
Abre http://localhost:3000 → arriba a la derecha deben aparecer los botones **Google** y/o **Discord** (si no hay ninguno configurado dice "Login no configurado").
Tras entrar verás tu nombre, el Top 5 y podrás guardar juegos. `http://localhost:8000/api/auth/me` debe devolver tu usuario.

## Cómo funciona (resumen)
- `GET /api/auth/{provider}/login` → guarda una cookie de *state* (anti-CSRF, 10 min) y redirige al proveedor.
- `GET /api/auth/{provider}/callback` → valida el *state*, canjea el *code*, exige **correo verificado**, crea/vincula el usuario y fija la cookie de sesión `ftg_session` (firmada, `HttpOnly`, `SameSite=Lax`, 30 días). Siempre redirige a `FRONTEND_URL`; los fallos añaden `?auth_error=<código>`.
- Si el mismo correo verificado entra por Google y por Discord, **es el mismo usuario** (se vinculan las dos identidades).
- `GET /api/auth/me`, `POST /api/auth/logout`, `GET /api/auth/providers`.
- Los tokens del proveedor no se guardan: solo se usan en el momento del login para leer el perfil.

## Producción (cuando toque)
`COOKIE_SECURE=true` (el backend se niega a arrancar con ese valor y el `SESSION_SECRET` de ejemplo), HTTPS en ambos dominios, redirect URIs con tu dominio real y `BACKEND_PUBLIC_URL`/`FRONTEND_URL`/`CORS_ORIGINS` actualizados. Frontend y backend deben ser *same-site* (p. ej. `app.tudominio.com` y `api.tudominio.com`) para que la cookie `SameSite=Lax` viaje en las peticiones `fetch`. Añade límite de peticiones a `/api/auth/*` (P4-02).
