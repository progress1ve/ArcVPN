# Local server credentials

Credentials are stored outside Git in `.secrets/server-credentials/` as Windows DPAPI-encrypted `PSCredential` XML. Encryption is bound to the current Windows user and machine. The tracked server inventory contains only aliases and non-secret topology.

Create or replace a credential without putting the password in chat or shell history:

```powershell
.\scripts\ops\server-vault.ps1 -Action Set -Alias pl-control -Username root
```

The command prompts securely. Use `-Action List` to show aliases only and `-Action Remove -Alias <name>` to remove one exact vault entry. Automation may capture `-Action Get -Alias <name>` into a `PSCredential` variable; it must never render `GetNetworkCredential().Password` or place it in command history/logs. Never commit `.secrets`, export decrypted values, or copy the vault to production.

For SSH automation, load the credential into the process environment, invoke `scripts/ops/ssh_exec.py`, and clear the variable in `finally`. The helper rejects unknown host keys; verify and add a host fingerprint out of band before first use.
