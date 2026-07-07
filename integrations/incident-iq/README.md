# Incident iQ — Custom Integration for the Sumo Logic Automation Service

A custom [Open Integration Framework](https://www.sumologic.com/help/docs/platform-services/automation-service/integration-framework/about-integration-framework/)
(OIF) integration for [Incident iQ](https://www.incidentiq.com/), the K-12
help desk platform. It mirrors the action set of Sumo Logic's out-of-the-box
[Zendesk integration](https://www.sumologic.com/help/docs/platform-services/automation-service/app-central/integrations/zendesk/):

| Action | Type | Endpoint |
| --- | --- | --- |
| Create Ticket | Notification | `POST /api/v1.0/tickets/new` (or `/tickets/simple/new` when a requestor email is given) |
| Update Ticket | Notification | `POST /api/v1.0/tickets/{id}` + `POST /api/v1.0/tickets/{id}/status/{statusId}` |
| Delete Ticket | Containment | `DELETE /api/v1.0/tickets/{id}` ⚠ see [Endpoint caveats](#endpoint-caveats) |
| Restore Deleted Ticket | Containment | `POST /api/v1.0/tickets/{id}/undelete` ⚠ see [Endpoint caveats](#endpoint-caveats) |
| Get Ticket Details | Enrichment | `GET /api/v1.0/tickets/{id}` |
| List Tickets | Enrichment | `POST /api/v1.0/tickets?$p=&$s=&$o=TicketCreatedDate&$d=` |
| List Users | Enrichment | `POST /api/v1.0/users?$p=&$s=&$o=FullName&$d=Ascending` |

## Files

```
incident-iq.yaml                # Integration definition — upload this first
actions/
├── create-ticket.yaml
├── update-ticket.yaml
├── delete-ticket.yaml
├── restore-deleted-ticket.yaml
├── get-ticket-details.yaml
├── list-tickets.yaml
└── list-users.yaml
tools/make_icon.py              # regenerates the placeholder icon (stdlib only)
```

Import steps live in the [repo README](../../README.md#using-an-integration).

## Resource configuration

All values come from **Incident iQ Administration ▸ Developer Tools**:

| Field | Required | Notes |
| --- | --- | --- |
| API URL | ✔ | Your district's base URL, e.g. `https://district.incidentiq.com` |
| API Token | ✔ | Sent as `Authorization: Bearer <token>` |
| Site ID | ✔ | Sent as the `SiteId` header on every request |
| Product ID | ✔ | Used by *Create Ticket*. Create **one resource per Incident iQ product** (e.g., IT Help Desk vs. Facilities) |
| Connection Timeout (s) | ✖ | Default 60 |
| Verify Server Certificate | ✖ | Default on |

The constant `Client: ApiClient` header required by the Incident iQ API is
hardcoded in every action script and is not configurable.

**Test connection** performs `POST /api/v1.0/users?$p=0&$s=1` — the cheapest
authenticated call that exercises all three auth headers without depending on
the Product ID or any ticketing configuration.

## Action reference

### Create Ticket (Notification)

Provide **exactly one** of *Requestor Email* or *Requestor ID*:

- *Requestor Email* → `POST /api/v1.0/tickets/simple/new` with `ForUserName`
  (Incident iQ resolves the user from the email/username).
- *Requestor ID* (user GUID) → `POST /api/v1.0/tickets/new` with `ForId`.

| Field | Required | Maps to |
| --- | --- | --- |
| Subject | ✔ | `Subject` |
| Description | ✔ | `IssueDescription` |
| Requestor Email | one of | `ForUserName` |
| Requestor ID | one of | `ForId` |
| Location ID | ✖ | `LocationId` |
| Issue Category ID | ✖ | `IssueCategoryId` |
| Urgent | ✖ | `IsUrgent` |

`ProductId` is injected from the resource. Outputs: `TicketId`,
`TicketNumber`, `Subject`, `StatusName`, `CreatedDate`, `IsUrgent`.

### Update Ticket (Notification)

Sends only the fields you fill as a partial body to
`POST /api/v1.0/tickets/{id}`. A *Status ID* is applied through the dedicated
`POST /api/v1.0/tickets/{id}/status/{statusId}` endpoint. The action then
re-fetches the ticket and returns its current state.

| Field | Required | Maps to |
| --- | --- | --- |
| Ticket ID | ✔ | path |
| Subject | ✖ | `Subject` |
| Description | ✖ | `IssueDescription` |
| Status ID | ✖ | status endpoint |
| Assigned To (user GUID) | ✖ | `AssignedToUserId` |
| Urgent (Urgent / Not urgent, unset = unchanged) | ✖ | `IsUrgent` |
| Extra Fields (raw JSON object) | ✖ | merged into the body — escape hatch for any other ticket property, e.g. `{"PriorityId": "..."}` |

*Urgent* is a three-state list — leave it unset to keep the ticket's current
value, or choose *Urgent* / *Not urgent* to change it.

### Delete Ticket / Restore Deleted Ticket (Containment)

Take a *Ticket ID* and return `{TicketId, Deleted: true}` /
`{TicketId, Restored: true}` (restore also echoes ticket fields when the API
returns them). Because both endpoints are inferred (see
[Endpoint caveats](#endpoint-caveats)), each action verifies its own outcome
before reporting success rather than trusting the HTTP status alone: *Delete
Ticket* re-reads the ticket and requires a 404 or `IsDeleted: true`, and
*Restore Deleted Ticket* fails if the echoed ticket still reports
`IsDeleted: true`.

### Get Ticket Details (Enrichment)

`GET /api/v1.0/tickets/{id}`. Outputs: `TicketId`, `TicketNumber`, `Subject`,
`IssueDescription`, `StatusName`, `CreatedDate`, `ModifiedDate`, `ClosedDate`,
`IsDeleted`, `IsUrgent`, `LocationName`, `AssignedToUserId`.

### List Tickets (Enrichment)

Paged via `$p` (page, default 0) and `$s` (page size, default 25), sorted by
created date. Optional single filter: pick a *Filter Facet* (`ticketnumber`,
`ticketstate`, `location`, `issuecategory`, `agent`, `team`, `prioritylevel`,
`asset`) and a *Filter Value* — if the value looks like a GUID it is sent as
`{"Facet": ..., "Id": ...}`, otherwise as `{"Facet": ..., "Value": ...}` (so
`ticketnumber` + `39181` works as-is). *Only Show Deleted* narrows the list to
deleted tickets — useful for finding a ticket to restore. Outputs
`Items.[].TicketId/TicketNumber/Subject/StatusName/CreatedDate/IsDeleted` and
`ItemCount`.

### List Users (Enrichment)

Paged via `$p`/`$s`, sorted by full name. Optional *Role ID* filters with
`$filter=(RoleId eq '<guid>')`; the *Raw $filter Expression* field passes any
Incident iQ `$filter` through untouched (power-user escape hatch, takes
precedence over Role ID). Outputs `Items.[].UserId/FullName/Email/Username/
RoleName/LocationName/IsActive/IsDeleted/SchoolIdNumber` and `ItemCount`.

## Finding GUIDs

Incident iQ references most things by GUID (statuses, locations, categories,
roles, users). To discover them:

- **Users/roles**: run *List Users* and read `UserId` / `RoleName` off the
  results.
- **Tickets**: run *List Tickets* or *Get Ticket Details* — the raw JSON in the
  action output contains the related `LocationId`, `IssueCategoryId`,
  `StatusTypeId`, etc. for existing tickets.
- Anything else: your Incident iQ **Developer Tools** console and
  [apihub.incidentiq.com](https://apihub.incidentiq.com/).

## Implementation notes

- **Response normalization**: Incident iQ wraps single objects in an `Item`
  envelope on some deployments and names the ticket status `StatusName`,
  `TicketStatusName`, or a nested `Status.Name` depending on endpoint/version.
  The single-ticket actions (*Get Ticket Details*, *Create Ticket*, *Update
  Ticket*, *Restore Deleted Ticket*) unwrap `Item` and coalesce the status into
  `StatusName`; the list actions normalize each element of the `Items` array
  instead. Either way the declared output paths stay stable.
- **Path IDs are GUID-validated**: any id spliced into a request path
  (`ticket_id`, `status_id`) and the `role_id` OData filter are checked against
  a GUID pattern before use, so an attacker-influenced incident artifact cannot
  redirect a request to another route or break out of the filter literal.
- **Scripts are self-contained**: OIF embeds the Python in each action YAML, so
  a common skeleton (env-var argparse, session headers, and — in the actions
  that make more than one call — a `call()` helper) is repeated across files.
  The two containment actions issue their single request inline instead.
- Scripts only use `requests`/`urllib3` + stdlib — all available in the
  standard `python3_generic:latest` image; no custom Docker image is needed.
- **Validate before uploading**: run `python3 tools/validate.py` to parse every
  YAML, `py_compile` each embedded script, and lint the field/output/table_view
  consistency.

## Endpoint caveats

`DELETE /api/v1.0/tickets/{id}` and `POST /api/v1.0/tickets/{id}/undelete` are
**inferred from Incident iQ's REST conventions** (the same patterns exist for
SLAs, funding sources, and assets) but are not in the public API
documentation. **Verify both against a throwaway ticket in a sandbox before
using them in production playbooks.** If ticket deletion turns out to be
unavailable to your API token, the documented fallback is to *cancel* the
ticket instead: use **Update Ticket** with your district's Cancelled status
GUID in *Status ID*.

Other assumptions to confirm on first live run (all cheap to adjust):

- `$p` paging is 0-based.
- `/tickets/simple/new` accepts the optional `LocationId` / `IssueCategoryId`
  / `IsUrgent` extras.
- List responses use `Items` / `ItemCount` envelope keys.

## Replacing the placeholder icon

The committed icon is a generic tile (no Incident iQ trademark), generated by
[`tools/make_icon.py`](tools/make_icon.py). To use your own logo:

```sh
base64 -i logo.png            # keep the PNG small — a few KB
```

Replace the `icon:` value in `incident-iq.yaml` with
`data:image/png;base64,<output>` and re-upload the integration YAML.
