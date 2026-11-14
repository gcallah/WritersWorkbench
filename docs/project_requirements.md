# Edited-volume author requirements

On the Projects page, select **Edited volume (multi-author)**. Before
creating it, check the items each author should provide. Other project types
do not use this form. Edit the saved choices later in the contributor editor.

| Checkbox | Project field | Folder |
| --- | --- | --- |
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
