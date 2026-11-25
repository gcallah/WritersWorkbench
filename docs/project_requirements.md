# Edited-volume author requirements

On the Projects page, select **Edited volume (multi-author)**. Before
creating it, check the items each author should provide. Other project types
do not use this form. Edit the saved choices later in the contributor editor.

| Checkbox | Project field | Folder |
| --- | --- | --- |
| #14 | `requires_bio` | A biography |
| #15 | `requires_permission` | Permission to publish |
| #16 | `requires_address` | An address |

New projects default to false for all three settings unless supplied at creation.
Older records with missing or NULL fields read as false without a migration.
Only actual JSON/Python booleans are accepted, not strings or integers.
An update that omits a setting preserves its saved value. False means not
required, not forbidden: editors may still save voluntarily provided materials.

These are separate from the per-contributor `Bio`, `Permission` and `Address`
receipt flags. No new fields are added to contributor records or stored files.
This change does not add document collection controls, reminders, or publishing
approval enforcement. Those are separate features.

## Handoff to Anemkal / project-management interface

The existing contributor editor contains working controls now. The pending
`/web` pages are not modified or merged by this work. Their existing create
calls will get false defaults; name/type updates will preserve saved settings.
No changes are required for those existing operations to keep working.

If the project create/edit forms should also expose the settings, use the exact
field names above and pass Python booleans to `projects.query.add/update`.
For an HTML checkbox, convert its submitted value to a boolean. When a form
actually contains all three checkboxes, include False for unchecked boxes so a
previous True can be turned off. Forms that do not contain the controls should
omit these fields. Pre-fill edit forms from `fetch_by_key()`.

The existing Projects API accepts and documents the same optional fields. Its
current access controls are unchanged. The contributor editor instead uses:

- GET `/Projects/requirements/<code>`
- PUT `/Projects/requirements/<code>`

(These moved from `/api/editor/projects/<code>/requirements` into the Projects
API in issue #22.)

These use the editor's existing shared Basic Auth. PUT requires same-origin
JSON, containing only one or more of the three boolean settings. Responses are
`{"requirements": {"requires_bio": false, "requires_permission": false,
"requires_address": false}}`. Missing projects return 404. Non-edited-volume
projects or invalid inputs return 400. Existing request protections apply.

The UI hides these controls in unassigned-contributor mode. It prevents saving
before settings have loaded, preserves checkbox choices on save failure, and
warns before switching projects or leaving with unsaved changes.

## Design notes for professor / team

We interpreted these as project-level requirements applying to each author,
not individual-author overrides. All default to No, keeping older projects
compatible. The professor can request different defaults or a mandatory initial
questionnaire. The author table/join-table work in #19 should continue treating
these as project settings, separate from each author's submission status.

## Manual check

1. Launch the server with editor credentials and open `/editor`.
2. Select an edited volume. Check one or more requirements and save.
3. Refresh, reselect the same project, and verify the saved choices.
4. Select another project and verify its choices are independent.
5. Uncheck a setting, save, refresh/reselect, and verify it remains unchecked.
6. Change a checkbox without saving and switch projects. Cancel the discard
   prompt to stay, or accept it to discard that unsaved change.
7. Confirm existing biographies, received flags, and other content remain.

Automated coverage is included in `make all_tests`: boolean validation, legacy
records, persistence, partial updates, project isolation, editor access,
existing Projects API compatibility, file/receipt preservation and save errors.
| A biography | `requires_bio` | bios |
| Permission to publish | `requires_permission` | permissions |
| An address | `requires_address` | addresses |
| An abstract | `requires_abstract` | abstracts |
| Keywords | `requires_keywords` | keywords |

All settings default to false, including missing fields on older records.
The project keeps its core chapters, drafts and Proposal folders. Checking
an item creates the corresponding folder; unchecking it never removes files.
Voluntary submissions create just the folder they need. Project settings do
not mark anything as received. Referee assignment remains a per-paper choice.

The Projects API accepts these boolean fields on creation and update. The
editor reads or updates them at `/api/editor/projects/<code>/requirements`
(GET or POST). Omitted fields are unchanged on update.
