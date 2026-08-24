# Local server credentials

Credentials are stored outside Git in `.secrets/server-credentials/` as Windows DPAPI-encrypted `PSCredential` XML. Encryption is bound to the current Windows user and machine. The tracked server inventory contains only aliases and non-secret topology.

Create or replace a credential without putting the password in chat or shell history:

```powershell
.\scripts\ops\server-vault.ps1 -Action Set -Alias pl-control -Username root
```

The command prompts securely. Use `-Action List` to show aliases only and `-Action Remove -Alias <name>` to remove one exact vault entry. Automation may capture `-Action Get -Alias <name>` into a `PSCredential` variable; it must never render `GetNetworkCredential().Password` or place it in command history/logs. Never commit `.secrets`, export decrypted values, or copy the vault to production.
