# Admin Console Security

## Access

Admin Console is protected by:

1. SSH tunnel
2. Nginx Basic Auth
3. Admin cookie session
4. CSRF token
5. ADMIN_API_KEY

## Create htpasswd for nginx Basic Auth

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd_admin adminops
sudo chown root:www-data /etc/nginx/.htpasswd_admin
sudo chmod 640 /etc/nginx/.htpasswd_admin
```

Expected permissions:

- owner/group: `root:www-data`
- mode: `640`
- non-root users cannot read the file

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
