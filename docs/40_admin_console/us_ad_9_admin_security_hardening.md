# US-AD-9 — Admin Console Security Hardening

Status: Planned

## User Story

As super_admin
I want additional security protection for Admin Console
So that internal admin endpoints cannot be brute-forced or discovered.

## Scope

Infrastructure hardening for `/admin/*` routes.

Features:

- Nginx Basic Auth
- Rate limiting
- protection against brute-force attempts

## Architecture

Security layers:

1. SSH tunnel
2. Nginx Basic Auth
3. Admin session cookie
4. CSRF protection
5. ADMIN_API_KEY for API endpoints

## Nginx protection

Paths:

/admin
/admin/*
/admin/ui/*
/admin/api/*

Must require:

Basic Auth

## Rate limiting

Apply rate limit for:

/admin/login

Suggested limits:

10 requests per minute per IP.

## Acceptance Criteria

- `/admin/*` protected by Nginx Basic Auth
- brute-force attempts limited
- admin endpoints still accessible via SSH tunnel
- no secrets logged

## Tests

Manual verification required:

- request without Basic Auth → 401
- valid Basic Auth → allowed
- rate limit exceeded → 429
