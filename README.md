# Sumo Logic Artifacts

A public collection of Sumo Logic artifacts — dashboards, and other reusable
content — that you can import into your own Sumo Logic environment.

## Contents

### Dashboards

| Dashboard | Description |
| --- | --- |
| [iboss - URL Overview](dashboards/iboss_-_URL_Overview.json) | Overview of iBoss web gateway URL logs: request volume, allowed vs. blocked traffic, categories, users, bandwidth, and malware/C2 flags. |

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

## Contributing

Issues and pull requests with new or improved artifacts are welcome.

## License

Released under the [MIT License](LICENSE).
