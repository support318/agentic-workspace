# GitHub Actions Setup Instructions

## Overview

This document provides instructions for setting up GitHub Secrets to enable auto-deployment via GitHub Actions.

## Required GitHub Secrets

Navigate to: https://github.com/support318/agentic-workspace/settings/secrets/actions

Click "New repository secret" and add the following:

### 1. SSH_PRIVATE_KEY

The private key for SSH access to the server.

**Value:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACCqE3+2iQWwBuCIP0VoQYWlvOqrkCIgYZdHfe02++CFCQAAAKgbC+7eGwvu
3gAAAAtzc2gtZWQyNTUxOQAAACCqE3+2iQWwBuCIP0VoQYWlvOqrkCIgYZdHfe02++CFCQ
AAAEDzXwfKG1BzhLA4gPjX0ZzY54cZX4Pyuvq+0rHUTuOt+KoTf7aJBbAG4Ig/RWhBhaW8
6quQIiBhl0d97Tb74IUJAAAAIGdpdGh1Yi1hY3Rpb25zQGFnZW50aWMtd29ya3NwYWNlAQ
IDBAU=
-----END OPENSSH PRIVATE KEY-----
```

### 2. SERVER_HOST

The IP address or hostname of the deployment server.

**Value:** `192.168.40.100`

### 3. SERVER_USER

The username for SSH access to the server.

**Value:** `candid`

### 4. SERVER_PATH

The path to the project directory on the server.

**Value:** `/home/candid/webhooks`

## Verification

After adding the secrets, verify the setup by:

1. Go to the "Actions" tab in the repository
2. Click on the most recent workflow run
3. Check that it completed successfully

## Troubleshooting

### SSH Connection Failed

- Verify the SSH_PRIVATE_KEY includes the `-----BEGIN` and `-----END` lines
- Check that the public key was added to `~/.ssh/authorized_keys` on the server
- Verify SERVER_HOST and SERVER_USER are correct

### Service Restart Failed

- Check that systemd services exist: `agentic-webhooks` and `email-processor`
- SSH into the server and run: `systemctl status agentic-webhooks`

## Local Key Location

The SSH keys are stored locally at:
- Private: `C:\Users\ryanm\.ssh\agentic-workspace\github_actions`
- Public: `C:\Users\ryanm\.ssh\agentic-workspace\github_actions.pub`

## Security Notes

- The SSH key was generated specifically for GitHub Actions
- It has no passphrase (required for GitHub Actions)
- The public key has been added to the server's authorized_keys
- Never share the private key
