# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| < 1.1   | :x:                |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in TestSpec, please report it
responsibly:

1. Email the maintainers via the project's [GitHub Issues](../../issues)
   with the subject line: `SECURITY: testspec vulnerability report`
2. Include a description of the vulnerability and steps to reproduce
3. Allow reasonable time for the maintainers to respond and address the issue

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 5 business days
- **Assessment**: We will assess the vulnerability and determine severity
- **Fix**: We will work on a fix and coordinate a release
- **Disclosure**: We will publicly disclose the vulnerability after a fix
  is available, giving credit to the reporter (unless they prefer anonymity)

## Security Best Practices for Users

- Always use the latest version of TestSpec
- Never commit `variables_override.yaml` or `.env` files to version control
- Use CI secrets for sensitive configuration values
- Review generated project templates before deploying
