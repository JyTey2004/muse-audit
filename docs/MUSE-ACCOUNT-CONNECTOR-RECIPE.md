# Native connector integration recipe — developer setup note only

Status: preparation only. No connector is registered, no native
tool exists yet from this note, no endpoint is invented here, no
credential is created or copied, no permission is changed, and
nothing is submitted. The endpoint, field names, and credential
setup are to be supplied only after the backend implementation
is reviewed. This note is separate from any final user result.

## 1. What the backend must supply first

- A hosted HTTPS endpoint, on port 443, for REST intake and
  uploads and for receipt persistence, plus a hosted HTTPS MCP
  endpoint for read-only taskflow tools. No local stdio command
  meets this interface.
- The bare API host names for those endpoints.
- The authentication scheme and, for OAuth, the issuer domain,
  authorize and token endpoints, token endpoint authentication
  method, scopes, and canonical MCP resource URI.
- The exact REST paths and field names for intake, upload,
  receipt creation, and receipt retrieval, and the exact MCP
  tool names and input schemas. These are not invented in this
  note; they must come from the reviewed backend.

Until those are supplied, the steps below cannot be completed,
and no connector should be registered.

## 2. connector.yaml — required fields

Save the descriptor beside its connector doc, with the same
lowercase slug used for the credential connection:

- id: equal to the folder name, in the form custom.<provider>,
  where <provider> is the slug supplied at connection time.
- title: the service's own name, which search also matches.
- description: one sentence on what the user can do through
  the connector. This is what the model sees in the connector
  list.
- include_in_prompt: true lists the connector in every
  conversation; false keeps it out of the list while search
  still finds it.
- require_auth: true hides the connector from the list while
  its credential is not connected. Use false only for a public
  API that needs no credential.
- aliases: optional, a list of other names users may call the
  service, so search finds it under those names too.

## 3. Authentication — allowed and declined schemes

The credential connection is created with the secure credential
flow, not by pasting a key in chat. The credential lives in the
registered connection, never in a file, helper, argument,
environment variable, or log. Helpers get a surrogate from the
bundled credential helper, which Muse swaps in only on an
approved request to a registered host, with redirects disabled
on authenticated requests.

Allowed schemes:

- api_key, with placement as one of: bearer_header,
  custom_header:<Header-Name>, query_param:<name>, or
  url_path_segment:<path containing {}>. Placement cannot be
  changed after setup.
- oauth2_code, with authorization_url, token_url,
  issuer_domain, token_endpoint_auth_method of
  client_secret_basic, client_secret_post, or none, and scopes.
  Optional: registration_url for dynamic client registration,
  and revoke_url where offered. For an OAuth-protected MCP
  server, resource is required: the canonical HTTPS resource
  URI from its protected-resource metadata or official docs.

Declined by name, with a reason to pass on: password,
session_cookie, signed_request, and multi_secret.

## 4. Registration order, once inputs are supplied

1. Call the secure credential flow with the provider slug,
   API hosts, and authentication details from section 3.
   The user completes the hosted connect link. Do not invent
   an authorization URL or substitute a raw scope.
2. Prove access with a harmless read, then with the exact
   operation asked for. The first real call is the proof;
   nothing checks the credential when it is saved.
3. Only after connection, run the scaffold tool for an
   already-connected custom connector. It copies the connector
   template and descriptor into place with slug, scheme, and
   hosts filled in, and never replaces an existing doc.
4. Build the helper in the connector's bin/ directory from
   the MCP client template, plus a REST helper for file
   transfers. The MCP template requires a fixed HTTPS endpoint
   on port 443, with no query, fragment, user info, or other
   port, and speaks Streamable HTTP with protocol versions
   2025-11-25, 2025-06-18, or 2025-03-26.
5. List tools, follow pagination until no cursor remains,
   read the live input schema of each operation needed, and
   add only those exact tool names to the allowed list. A tool
   the server adds later stays blocked until reviewed and added.
6. Complete the connector doc with verified commands, inputs,
   outputs, pagination, limits, and recovery. Label any
   operation not run as untested, and delete template comments.
   Do not document a tool that has not been reviewed.

## 5. How native tools are exposed and discovered

- A connector is found through the connector list and search.
  With include_in_prompt true it is listed in every
  conversation; with false it is found by search only. With
  require_auth true it is hidden while not connected.
- In a normal file request, the agent discovers tools with
  list-tools, which returns the reviewed tools, their live
  input schemas, and whether each is treated as a read or a
  write. Unknown or new provider tools stay unavailable until
  reviewed.
- A tool is called with call-tool, with arguments as one JSON
  object built from that schema. Tool names and required fields
  are never guessed.
- Reads and writes follow the user's connector settings.
  Manage, delete, and other sensitive operations ask for
  approval by default, and connector approval is separate
  from any other approval. This recipe does not override any
  safety, policy, or approval control, and it does not use a
  saved skill to force a tool call.

## 6. How selected task and file bytes reach the backend

- Only files selected for the current task are sent: the
  user's supplied files for that task, or files generated
  for that task. No other workspace files are sent.
- MCP call arguments are a single JSON object. Large file
  bytes are not put in that object. For full file transfers,
  use the REST upload path, as in the documented file
  connectors: a local-file upload command transfers the file,
  with its name, size, hash, and MIME type where the live
  schema requires them, and returns a file, task, or receipt
  identifier.
- Pass that returned identifier, not the file bytes again,
  to the MCP review tool. The backend persists the intake,
  the uploaded file, and the receipt under that identifier.
- On a 401 or 403, first check that the request carried the
  credential, that the host is registered, and that placement
  and scopes match. Reconnect only when a request that carried
  the credential is still rejected. After an uncertain write,
  inspect the current state before retrying; the first request
  may have completed. A write is never replayed automatically
  after a timeout or session end.

## 7. How results return to one chat view

- The connector helper returns JSON. Check both the CLI exit
  status and the provider result, including any error flag;
  an outer success flag does not guarantee provider success.
- Retrieve the persisted receipt by its task or receipt
  identifier, using the backend's retrieval path supplied
  after review. Do not invent that path here.
- In chat, render from the receipt fields only: a short
  result in one sentence, a small table of checks with
  requirement, status, observed, expected, and reason, every
  failure, missing input, and material unsupported or
  unverified claim, one scope sentence stating that checks
  cover the interpreted checklist and that meaning and
  real-world accuracy may still need user review, and a
  short receipt reference with links to the result file and
  to the readable receipt.
- Keep machine JSON, logs, and protocol details out of the
  main chat answer, unless the user asks for raw diagnostics.
  If verification cannot run, say so plainly and present
  any file as unverified for that step.

## 8. Inputs still needed after backend review

- Hosted HTTPS REST and MCP endpoint URLs, with API hosts.
- Authentication scheme, placement or OAuth details, and
  MCP resource URI where applicable.
- REST intake, upload, and receipt paths and field names.
- MCP tool names, input schemas, and allowed-tool list.
- Approval defaults for read, upload, and receipt operations.

None of these is supplied by this note, and no native tool
exists until they are supplied, connected, verified with a
harmless read, documented, and reviewed.
