# Sumo Logic Artifacts

A public collection of Sumo Logic artifacts — dashboards, playbooks,
integrations, and other reusable content — that you can import into your own
Sumo Logic environment.

## Contents

### Dashboards

| Dashboard | Description |
| --- | --- |
| [iboss - URL Overview](dashboards/iboss_-_URL_Overview.json) | Overview of iBoss web gateway URL logs: request volume, allowed vs. blocked traffic, categories, users, bandwidth, and malware/C2 flags. |

### Playbooks (Automation Service)

| Playbook | Description |
| --- | --- |
| [Account Takeover - Identity Containment](automations/playbooks/account-takeover-identity-containment/) | Analyst-initiated ATO response: validate the user in Azure AD, gate on analyst approval, then revoke Azure AD sessions, reset the on-prem AD password (synced to Azure AD and Google Workspace), and suspend/re-enable the Google Workspace account to invalidate Google sessions. |

### Integrations (Automation Service)

| Integration | Description |
| --- | --- |
| [Incident iQ](integrations/incident-iq/) | Custom Open Integration Framework integration for the Incident iQ K-12 help desk, mirroring the OOTB Zendesk action set: Create Ticket, Update Ticket (Notification); Delete Ticket, Restore Deleted Ticket (Containment); Get Ticket Details, List Tickets, List Users (Enrichment). |

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

## Using an integration

Custom integrations are built with the Sumo Logic
[Open Integration Framework](https://www.sumologic.com/help/docs/platform-services/automation-service/integration-framework/about-integration-framework/):
one integration definition YAML plus one YAML per action, with the action's
Python embedded. The files upload to the Automation Service as-is — no
archive packaging step (unlike playbooks).

### Prerequisites

- Sumo Logic Automation Service enabled for your org.
- A deployed [Automation Bridge](https://help.sumologic.com/docs/platform-services/automation-service/automation-service-bridge/) —
  **custom integrations execute on your Bridge, not in Sumo's cloud.** The
  Bridge host needs outbound HTTPS to your Incident iQ site
  (`https://<district>.incidentiq.com`).
- Incident iQ **API Token**, **Site ID**, and **Product ID**, all from
  **Incident iQ Administration ▸ Developer Tools**.

### Import

1. In Sumo Logic, go to **Automation ▸ Integrations** and click the **+** icon.
2. In the **New Integration** dialog, click **Upload File** and upload
   [`incident-iq.yaml`](integrations/incident-iq/incident-iq.yaml). An
   *Incident iQ* integration is created.
3. Open the new integration, hover over its name, and click the **Upload**
   button that appears. In the **Upload** dialog select Type **Action**, then
   upload each of the seven files under
   [`integrations/incident-iq/actions/`](integrations/incident-iq/actions/).
4. Click the **+** button next to **Resources** and fill in the resource:
   API URL, API Token, Site ID, Product ID, and select your **Automation
   Bridge** as the automation engine.
5. Click **Test** to validate the connection, then **Save**.

Per-action fields, outputs, and GUID-discovery tips are documented in the
[integration README](integrations/incident-iq/README.md).

> **Note:** the *Delete Ticket* and *Restore Deleted Ticket* endpoints are
> inferred from Incident iQ's REST conventions and are not in the public API
> docs — verify both against a throwaway ticket in a sandbox before using
> them in production playbooks. Fallback if delete is unavailable: use
> *Update Ticket* to set the ticket to your district's Cancelled status.

> **Note:** the Product ID binds a resource to one Incident iQ product
> (e.g., IT Help Desk). If your district runs several products, create one
> resource per product.

## Contributing

Issues and pull requests with new or improved artifacts are welcome.

## License

Released under the [MIT License](LICENSE).
