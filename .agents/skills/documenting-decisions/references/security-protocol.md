# Security protocol

Never auto-commit changes to these paths without human review:

- auth/, login/, session/, permission/, rbac/
- Any file containing crypto, hashing, or token operations
- Any file that opens network connections or modifies CORS/CSP
- Any SQL that uses string interpolation or concatenation

When modifying these paths, add a SEC section to DECISION_LOG.md explaining:

- What security property you're maintaining or changing
- What input validation exists
- What could go wrong if this code has a bug
