# SCENE QR | Project Showcase

> Multi-business QR experience and request-management SaaS — public beta engineering project.

## The problem
Physical locations often depend on verbal requests, paper signs, or disconnected communication. SCENE QR explores how a scan can turn a location into a branded mobile interaction connected to a staff workflow.

## What the project demonstrates
- QR station creation and rotation
- Mobile-first guest request and private receipt flows
- Owner, manager, and staff access boundaries
- Request queues, service catalogs, and business-specific settings
- Automated API, browser, and database regression testing

## Engineering approach
The current pilot uses Python/FastAPI, a web frontend, and SQLite by default. PostgreSQL transition work is experimental. The application separates guest interactions from authenticated business administration and tests tenant boundaries.

## Current maturity
**Pilot/beta, not production-certified.** Payments, production-grade account recovery, provider-delivered notifications, and broader operations controls remain unfinished. A guest request is not a paid order or confirmed appointment.

## Explore
- [Repository](https://github.com/greenlight3676-art/scene-qr-saas)
- [Setup, test instructions, limitations](../README.md)
- [Deployment checklist](../DEPLOYMENT_CHECKLIST.md)
- [Architecture roadmap](../SCENE_PLATFORM_BLUEPRINT.md)

## What I would build next
1. Verify production identity and tenant authorization end to end.
2. Harden persistence, backups, observability, and deployment.
3. Validate a complete real-world merchant pilot before charging customers.

**Developer:** Daniel Lundy — software engineering, AI systems, and digital business products.
