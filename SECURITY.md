# Security Policy

## Supported Versions

We actively support the following versions of TracLine with security updates:

| Version | Supported          | Notes                           |
| ------- | ------------------ | ------------------------------- |
| 2.0.0+  | ✅ Active Support  | Current version, all features   |
| 1.x     | ❌ End of Life     | No longer supported             |

**Note**: TracLine 2.0.0 is a complete rewrite. Version 1.x is no longer maintained and users should upgrade to 2.x for security updates and new features.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in TracLine, please follow these steps:

### 1. Do Not Create Public Issues

Please do not create public GitHub issues for security vulnerabilities. This helps protect users who may not have updated yet.

### 2. Report Privately

Send your vulnerability report via:
- **GitHub Security Advisories**: Use the "Security" tab in the repository
- **Email**: Contact the maintainers directly through GitHub

Include the following information:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if you have one)

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (see below)

### 4. Severity Levels

#### Critical (Fix within 24-48 hours)
- Remote code execution
- SQL injection
- Authentication bypass
- Data exposure of sensitive information

#### High (Fix within 1 week)
- Privilege escalation
- Cross-site scripting (XSS)
- Local file inclusion
- Significant data leakage

#### Medium (Fix within 2 weeks)
- Denial of service
- Information disclosure
- CSRF vulnerabilities

#### Low (Fix within 1 month)
- Minor information leakage
- Non-security bugs with privacy implications

## Security Best Practices

### For Users

1. **Keep TracLine Updated**: Always use the latest version
2. **Secure Configuration**: 
   - Use strong passwords for database connections
   - Set up proper firewall rules
   - Enable HTTPS in production
3. **Environment Variables**: Store sensitive data in environment variables, not config files
4. **Regular Backups**: Backup your data regularly
5. **Monitor Logs**: Check application logs for suspicious activity

### For Contributors

1. **Code Review**: All code changes require review
2. **Dependency Updates**: Keep dependencies updated
3. **Security Testing**: Run security scans before submitting PRs
4. **Sensitive Data**: Never commit passwords, tokens, or other sensitive data

## Security Features

TracLine includes several security features:

- **Input Validation**: All user inputs are validated and sanitized
- **SQL Injection Prevention**: Uses parameterized queries
- **CSRF Protection**: Cross-site request forgery protection
- **File Upload Security**: Restricted file types and size limits
- **Authentication**: Secure session management
- **Logging**: Comprehensive audit logging

## Configuration Security

### Database Security
```yaml
# Good - Using environment variables
database:
  password: ${TRACLINE_DB_PASSWORD}

# Bad - Hardcoded password
database:
  password: "mypassword123"
```

### GitHub Token Security
```bash
# Good - Environment variable
export GITHUB_TOKEN=ghp_your_token_here

# Bad - In configuration file
github:
  token: "ghp_your_token_here"
```

## Updates and Patches

Security updates are released as soon as possible after a vulnerability is confirmed. We recommend:

1. **Subscribe to Releases**: Watch this repository for release notifications
2. **Test Updates**: Test security updates in a staging environment first
3. **Apply Quickly**: Apply critical security updates within 48 hours

## Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities. Contributors who report valid security issues may be acknowledged in:

- Release notes
- Security advisories  
- Hall of fame (if you consent)

Thank you for helping keep TracLine and its community safe!