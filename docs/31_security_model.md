### Admin Console Protection

Admin console uses layered security:

1. SSH tunnel access only
2. Nginx Basic Auth
3. Cookie session authentication
4. CSRF protection
5. API key protection

Sensitive values must never appear in logs.
