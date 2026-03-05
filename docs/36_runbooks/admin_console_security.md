# Admin Console Security

## Access

Admin Console is protected by:

1. SSH tunnel
2. Nginx Basic Auth
3. Admin cookie session
4. CSRF token
5. ADMIN_API_KEY

## Creating admin password

Command:

htpasswd -c /etc/nginx/.admin_htpasswd admin

## Reload nginx

sudo systemctl reload nginx

## Test access

curl -I http://localhost/admin

Expected:

401 Unauthorized

### Security verification checklist

- /admin requires Basic Auth
- unauthenticated request returns 401
- valid credentials allow access
- rate limit triggers on repeated requests
