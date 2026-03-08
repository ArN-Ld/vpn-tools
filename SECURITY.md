# Security Policy

## Supported Versions

We actively maintain security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

As this is an active fork under development, we recommend always using the latest commit from the `main` branch.

## Security Considerations

### Privilege Requirements

This tool requires `sudo` privileges for MTR (My TraceRoute) network diagnostics. Please be aware:

- **Review code before running with sudo**: Always audit scripts that require elevated privileges
- **Minimize exposure**: Only run with sudo when performing actual tests
- **Non-root alternatives**: Where possible, configure MTR with capabilities instead of requiring full sudo

### Data Privacy

The tool handles the following data:

- **Network performance metrics**: Download/upload speeds, latency, packet loss
- **Geographic information**: Your location (from input or geocoding)
- **VPN server information**: Mullvad server hostnames and IPs
- **Local storage**: Results stored in `runtime/mullvad_results.db` (SQLite)

**No sensitive data is transmitted** to external services except:
- Speedtest.net servers (for bandwidth testing)
- OpenStreetMap/geocoding services (if geopy is used for location lookup)

All data remains **local** on your system.

### Dependencies

We use automated dependency scanning via:
- **Dependabot**: Weekly checks for vulnerable dependencies
- **GitHub Actions CI**: Validates code syntax and runs tests

### VPN Security

- This tool **tests** VPN connections but does not manage VPN security policies
- Always verify you're connected to the intended VPN server before running sensitive operations
- Test results may reveal your geographic location to the VPN provider

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow responsible disclosure:

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Send a detailed report to the repository maintainer via:
   - GitHub Security Advisory (preferred): Use the "Security" tab → "Report a vulnerability"
   - Direct contact to [@ArN-Ld](https://github.com/ArN-Ld) via GitHub private message

### What to Include

Please provide:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)
- Your contact information for follow-up

### Response Timeline

- **Initial response**: Within 48 hours of report
- **Status update**: Within 7 days with assessment and timeline
- **Resolution**: Depends on severity, but critical issues will be prioritized

### Disclosure Policy

- We will work with you to understand and validate the issue
- We will credit you in the fix (unless you prefer to remain anonymous)
- We will coordinate public disclosure after a fix is available
- Typical embargo period: 90 days or until fix is deployed, whichever comes first

## Security Best Practices for Users

1. **Keep dependencies updated**: Run `pip install --upgrade -r requirements.txt` regularly
2. **Review Dependabot PRs**: Check and merge security updates promptly
3. **Audit before sudo**: Review code changes before running with elevated privileges
4. **Isolate test environment**: Consider running tests in a dedicated VM or container
5. **Monitor logs**: Check `runtime/` directory for unexpected behavior
6. **Verify sources**: Only clone from official repository sources

## Additional Resources

- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Mullvad Privacy Policy](https://mullvad.net/en/help/privacy-policy/)
- [GitHub Security Advisories](https://github.com/ArN-Ld/vpn-tools/security/advisories)

## Acknowledgments

We appreciate the security research community and will acknowledge contributors who help improve the security of this project.

---

**Note**: This project is a fork of [valtumi/vpn-tools](https://github.com/valtumi/vpn-tools). Security issues in the upstream project should be reported to the original maintainer.
