# Sumo Logic Artifacts

A public collection of Sumo Logic artifacts — dashboards, playbooks, and other
reusable content — that you can import into your own Sumo Logic environment.

## Contents

### Dashboards

| Dashboard | Description |
| --- | --- |
| [iboss - URL Overview](dashboards/iboss_-_URL_Overview.json) | Overview of iBoss web gateway URL logs: request volume, allowed vs. blocked traffic, categories, users, bandwidth, and malware/C2 flags. |

### Playbooks (Automation Service)

| Playbook | Description |
| --- | --- |
| [Account Takeover - Identity Containment](automations/playbooks/account-takeover-identity-containment/) | Analyst-initiated ATO response: validate the user in Azure AD, gate on analyst approval, then revoke Azure AD sessions, reset the on-prem AD password (synced to Azure AD and Google Workspace), and suspend/re-enable the Google Workspace account to invalidate Google sessions. |

## Using a dashboard

These dashboards are exported in Sumo Logic's **DashboardV2SyncDefinition**
(Terraform / Content API) format.

**Import via the UI**

1. In Sumo Logic, open the folder where you want the dashboard.
2. Choose **Add ▸ Import** (or the folder's **⋯ ▸ Import** menu).
3. Paste the contents of the `.json` file and confirm.

**Configure the source category**

Each dashboard uses a `sourceCategory` template variable so it can be pointed at
your own data. After importing, set the `sourceCategory` variable to the
`_sourceCategory` of the relevant logs — for the iBoss dashboard, your iBoss URL
logs.

### iboss - URL Overview panels

- **KPIs:** Total Requests, Allowed, Blocked / Not Allowed, Unique Users, Total
  Bandwidth (GB), Malware / C2 Flagged
- **Trends:** Requests Over Time by Action, Bandwidth Over Time (MB)
- **Top talkers:** Top 10 Categories, Hosts, Users by Requests, Users by
  Bandwidth, Applications, Source IPs
- **Security & compliance:** Blocked Requests by Category, Response Codes,
  Requests by Location, Recent Blocked / Flagged Requests

## Using a playbook

Playbooks target the Sumo Logic **Automation Service** (included with Cloud
SIEM / Cloud SOAR entitlements) and are shared in the playbook JSON
export/import format.

### Prerequisites

- Sumo Logic Automation Service enabled for your org.
- The following integrations installed from **App Central** and configured with
  a resource (credentials) in **Automation ▸ Integrations**:
  - **Azure AD** — used for *Get User* and *Revoke Sign In Sessions*. Requires
    an Azure app registration with Microsoft Graph application permissions
    (e.g., `User.ReadWrite.All`) and the *User Administrator* role for
    password-related actions.
  - **Active Directory V2** — used for *Reset Password* against on-prem AD.
    Requires a deployed [Automation Bridge](https://help.sumologic.com/docs/platform-services/automation-service/automation-service-bridge/)
    with network reach to a domain controller.
  - **Google Workspace IDP** — used for *Suspend User* / *Enable User*.
- Password sync from on-prem AD to Azure AD (e.g., Entra Connect) and to
  Google Workspace (e.g., GCDS/Password Sync), so the on-prem reset propagates
  to both clouds. If you don't sync passwords, add cloud-native reset actions
  instead.

### Import

Playbooks are shared in the Automation Service **Export All (ZIP Format)**
bundle layout: a `tar.gz` archive of YAML files named
`<unique_id>.<name>.<file_type>.yaml` (see the
[playbook docs](https://www.sumologic.com/help/docs/platform-services/automation-service/playbooks/create-playbooks/#export-and-import-playbooks)).
The repo stores the bundle's files unpacked (so they diff nicely); package and
import them like this:

1. Build the archive (file names inside must stay exactly as-is — the playbook
   references its sibling files by name):

   ```sh
   cd automations/playbooks/account-takeover-identity-containment
   tar -czf Account_Takeover_-_Identity_Containment.tar.gz *.yaml
   ```

2. In Sumo Logic, go to **Automation ▸ Playbooks**.
3. Click the **Import** icon and select the `.tar.gz` file.

The bundle also carries `Type.imsfield` / `Account-Takeover.imslistvalue`
definitions so the playbook imports with an "Account Takeover" type, mirroring
how real exports package the playbook type.

> **Note:** integration and action definitions are cryptographically signed by
> Sumo Logic and are therefore *not* included — install the integrations from
> App Central instead, then bind each action node to your resources
> (see below). A legacy-format JSON export
> ([Account_Takeover_-_Identity_Containment.json](automations/playbooks/Account_Takeover_-_Identity_Containment.json))
> is kept for Terraform (`sumologic_csoar_playbook`) and older Cloud SOAR
> tenants, whose import instead expects a ZIP containing
> `playbook_to_import.json`.

### Post-import wiring (required)

Imported playbooks are **not runnable out of the box** — this matches how Sumo
Logic ships its own published playbooks. Action nodes carry the intended
integration/action in their titles, but you must bind each one to *your*
configured integration resource and fill in its fields:

1. On the Start node, choose **Add New Param** and add a `user_upn` parameter
   (the target user's UPN / primary email). The analyst supplies the value each
   run; nodes reference it as `{{params.user_upn}}`.
2. Open each action node, select the integration resource and action, and set
   the fields:

   | Node | Integration ▸ Action | Key fields |
   | --- | --- | --- |
   | Validate User | Azure AD ▸ Get User | User = `{{params.user_upn}}` |
   | Revoke Azure AD Sessions | Azure AD ▸ Revoke Sign In Sessions | User = `{{params.user_upn}}` |
   | Reset On-Prem AD Password | Active Directory V2 ▸ Reset Password | Account = `{{params.user_upn}}`; new password per your org policy |
   | Suspend Google Workspace User | Google Workspace IDP ▸ Suspend User | User email = `{{params.user_upn}}` |
   | Re-enable Google Workspace User | Google Workspace IDP ▸ Enable User | User email = `{{params.user_upn}}` |

   Action names can vary slightly between integration versions — pick the
   closest matching action in your installed version.
3. On the **user choice** node, set the authorizer (who may approve
   containment). The gate expires after 4 hours and defaults to **Abort** —
   intentionally the safe default.
4. **Save and publish** the playbook, then validate: the canvas shows 9 nodes,
   each action node opens with its integration bound, and a dry run against a
   **test account** completes end-to-end.

### Safety caveats

- **The password reset is destructive** — the user is locked out until you
  hand off the new credentials. Run only against confirmed account takeovers,
  with your normal IR/change approvals.
- **Suspend briefly locks the Google account** and suspension/sync propagation
  can take a few minutes. If your AD→Google password sync is slow, consider
  inserting a *Sleep* action between the password reset and the suspend step.
- The approval gate exists on purpose: nothing destructive runs until an
  authorized analyst picks **Contain**.

### Roadmap

Planned follow-ups for evidence-based containment (no out-of-the-box Sumo
integrations exist for these today): adding confirmed malicious domains to the
iBoss URL blocklist, and blocking attacker IPs via Microsoft Entra Conditional
Access named locations / Google Context-Aware Access.

## Contributing

Issues and pull requests with new or improved artifacts are welcome.

## License

Released under the [MIT License](LICENSE).
