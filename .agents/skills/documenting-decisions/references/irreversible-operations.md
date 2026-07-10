# Irreversible operations

Never execute these without explicit human approval:

- Database migrations (create the migration file, do not run it)
- File or data deletion operations
- Deployment triggers
- External API calls with side effects (payments, webhooks, notifications)

Flag all irreversible operations in DECISION_LOG.md under IRREV.
