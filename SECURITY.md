# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.2.x   | :white_check_mark: |
| 3.1.x   | :white_check_mark: |
| < 3.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please email security@example.com or create a private security advisory on GitHub.

**Please do not create public issues for security vulnerabilities.**

## Security Best Practices

### Environment Variables

**Never commit sensitive credentials to the repository:**

- ❌ `.env` files with real credentials
- ❌ API keys, passwords, tokens in code
- ❌ Database credentials in scripts

**Always use:**

- ✅ `.env.example` files as templates
- ✅ Environment variables for secrets
- ✅ `.gitignore` for sensitive files

### Configuration Files

The following files should **never** be committed:

```
.env
.env.worker
*.key
*.pem
credentials.json
secrets.yaml
```

### Required Configuration

Copy example files and configure with your own credentials:

```bash
# Copy configuration templates
cp .env.example .env
cp .env.worker.example .env.worker

# Edit with your credentials
nano .env
nano .env.worker
```

### Database Security

- Use strong passwords for database users
- Limit database user permissions to necessary operations
- Use environment variables for database credentials
- Never hardcode credentials in scripts

### API Security

- Store API keys in `.env` files
- Never commit API keys to version control
- Rotate API keys regularly
- Use rate limiting for all endpoints

### Production Deployment

1. **Never use default credentials**
   - Change all default passwords
   - Generate strong, unique passwords
   - Use password managers

2. **Environment separation**
   - Use different credentials for dev/staging/production
   - Never use production credentials locally
   - Keep production secrets in secure vaults

3. **Access control**
   - Limit who has access to production credentials
   - Use SSH keys, not passwords
   - Enable 2FA for all accounts

4. **Monitoring**
   - Monitor for unauthorized access attempts
   - Set up alerts for suspicious activity
   - Regularly review access logs

## Security Features

### Circuit Breaker Pattern

The system implements circuit breaker patterns to prevent cascading failures:

- OpenAI API calls
- Database operations
- RSS feed fetching

Monitor circuit breaker status at: `/api/v1/health/circuit-breakers`

### Error Recovery

- Automatic retry with exponential backoff
- Error classification and targeted recovery
- Rate limiting to prevent abuse

### Health Checks

- Kubernetes-ready liveness/readiness probes
- Database connectivity monitoring
- Service health tracking

## Security Audit History

### 2025-09-30
- **Critical Fix**: Removed hardcoded database credentials from repository
- Moved `.env.worker` to `.gitignore`
- Created `.env.worker.example` template
- Removed hardcoded password from `scripts/update_all_docs.sh`

### 2025-09-30
- Implemented Circuit Breaker pattern for fault tolerance
- Added comprehensive error recovery mechanisms
- Enhanced monitoring endpoints

## Compliance

- All sensitive data must be encrypted at rest
- API communications should use HTTPS in production
- Follow OWASP security guidelines
- Regular security audits recommended

## Contact

For security concerns, contact: security@example.com

---

*Last Updated: 2025-09-30*
