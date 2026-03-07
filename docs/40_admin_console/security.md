# Admin Console Security

## Current security baseline

### Infrastructure access layer

Admin Console routes (`/admin`, `/admin/*`) are protected on Nginx edge by Basic Auth in
`/etc/nginx/sites-enabled/zumbot.ru`:

```nginx
location = /admin {
    auth_basic "Restricted Admin";
    auth_basic_user_file /etc/nginx/.htpasswd_admin;

    proxy_pass http://127.0.0.1:8000/admin;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

location /admin/ {
    auth_basic "Restricted Admin";
    auth_basic_user_file /etc/nginx/.htpasswd_admin;

    proxy_pass http://127.0.0.1:8000;
}
```

> `.htpasswd_admin` is server-local and **must not** be stored in git.

Provisioning commands on VPS:

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd_admin adminops
sudo chown root:www-data /etc/nginx/.htpasswd_admin
sudo chmod 640 /etc/nginx/.htpasswd_admin
```

### Application authentication

Admin login uses:

- `admin_session` cookie

Unauthenticated requests return:

- `404`

### CSRF

- `POST /admin/ui/*` endpoints require CSRF token.

### Audit

All admin actions write record to:

- `admin_audit_log`

### Sensitive data

- Tokens and secrets must be removed from payload.

### Access verification

Expected behavior:

- Opening `https://zumbot.ru/admin` prompts for Basic Auth credentials.
- After successful Basic Auth, request is proxied to backend admin endpoints.
