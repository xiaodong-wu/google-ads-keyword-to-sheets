# Chrome access and verified CSV downloads

Read this before opening Google Ads. Keep Keyword Planner as the live data source; adapting the
browser controller does not change the query, filters, output mode, or CSV verification contract.

## Select an available controller

1. Honor an explicitly requested browser/controller. Otherwise use the available supported tool
   that controls the user's Chrome session; `mcp__cua_repl` is suitable when enabled. Read its
   entry-point instructions and returned API documentation before acting. Discover the Chrome
   browser/profile and tabs using its supported inventory; do not assume Chrome is the currently
   selected browser or substitute an unsigned-in embedded browser.
2. If `chrome:control-chrome` is installed and its tools are callable, it is also an option. Read
   it before using its tools. Its absence alone does not require installation or block the job.
3. Selecting an available Chrome controller for the same authorized query, download, and local
   export does not itself require another confirmation. Follow actual tool permission and
   handoff requirements when they arise; this rule does not override them or authorize account
   changes, ad publication, or additional online writes.
4. If no supported tool can connect to Chrome, record `blocked: browser_unavailable` and explain
   the missing connection. Do not invent tool methods, install a plugin automatically, extract
   browser cookies, or use a different automation channel to bypass tool restrictions.

For `mcp__cua_repl`, use its documented browser inventory and tab APIs, explicitly select Chrome,
then reuse that binding. Keep browser actions in that tool; shell/Python use is limited to the
downloaded data files and CSV processing. Use fresh visible UI/DOM state to confirm the active
seed and targeting. Any policy block is a blocker, not permission to switch tools to bypass it.

## Download the actual export

Use the **Download keyword ideas → .csv** action after the on-screen query settings have been
verified. Do not replace the export with a copied result table, estimated values, an API call,
or another batch's file.

- If the controller documents a download event and a file-save/path method, use those exact APIs.
  Arm a supported download event before clicking the CSV option. A `waitForEvent("download")`
  method alone does not imply that the returned object has `path()` or `saveAs()`.
- If no path API is provided, use a supported Downloads UI to observe the completed file and its
  name/path. A download that is still in progress, interrupted, or blocked is not complete.
- When the local download directory is known from the tool, browser UI, or user configuration,
  take a bounded snapshot of that directory immediately before exporting. After the UI action,
  compare new/changed files within that same directory and export time window. Consider only
  completed CSV candidates; ignore temporary partial-download files. Do not recursively scan the
  home directory, browser profile, history databases, or unrelated download contents.
- Require an unambiguous link between the query and the file: observed download filename or
  completion UI, export timing, stable completed file, recognized Google Ads CSV structure, and
  consistency with available metadata and the visible result rows. Do not blindly use the newest
  CSV. If multiple candidates remain plausible, resolve them through the download UI before use.
- If neither documented APIs nor supported UI/local-file evidence can identify the export,
  record `blocked: download_unresolved`. Request only the missing file or connection needed to
  continue; retain successful batches.

If the export opens a Chrome blocked page (for example `ERR_BLOCKED_BY_CLIENT` on the report
storage host), record `blocked: download_blocked_by_client` and ask the user to resolve the
browser/extension restriction. Preserve the tab for handoff. Do not replay the signed download
URL through HTTP tools, another browser, or an API to bypass the restriction, and do not put
signed URLs or their tokens in the audit manifest or repository.

Copy the identified original file unchanged into the job's audit directory without overwriting
another batch. Record its SHA-256, export timestamp, browser tool, download filename/path evidence,
seed, language, location, Google network, actual date range, and currency when visible. Keep
observed values separate from requested settings and mark unavailable values `not verified`.
Do not store cookies, credentials, browser session tokens, or unrelated account information.

Parse that copied file with `scripts/keyword_workflow.py`. Detailed export mode still requires the
complete original columns and per-keyword metric values, followed by an exact readback comparison.
The parent multi-seed workflow must perform this process separately for each seed, in sequence.
