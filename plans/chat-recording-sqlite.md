# SQLite chat recording and reconstruction

Status: proposed implementation plan. No recorder is implemented by this document.

## Goal

Keep an application-owned, durable record of conversations across users, threads,
turns, and process restarts. Support faithful transcript reconstruction and analysis
without depending on LangSmith retention or the agent's current, possibly summarized,
message history. Start with SQLite for this single-host workbench.

The archive must preserve original message content and formatting, structured content
blocks, tool calls/results, model inputs/outputs, timing, ordering, ownership, and
execution relationships. Preserve available metadata in addition to indexed columns;
explicitly exclude credentials. Record unavailable values as unknown rather than
inventing timestamps, identities, or model revisions.

## Scope and terminology

- **User:** verified Supabase user ID, stable across browser sessions. Email is optional
  descriptive metadata and must not be used as the ownership key.
- **Conversation/thread:** Agent Server thread, scoped by an installation/deployment ID
  so identical IDs from separate environments cannot collide in a combined export.
- **Turn:** an accepted user submission or explicit continuation/resume operation.
  It can produce several model calls and assistant/tool messages before completion.
- **Execution/attempt:** one Agent Server run or retry within a turn. Distinguish a
  transport retry from a deliberate new user submission.
- **Message:** a logical user, assistant, system, developer, or tool message. A message
  can have revisions and be reused in many model requests.
- **Invocation:** one model or tool call, including internal summarization calls.
- **Event:** an immutable observation, such as message acceptance, a streaming delta,
  completion, interruption, cancellation, or a state edit.

Maintain two separate reconstruction views:

1. **Conversation transcript:** each logical message once, with revisions, branches,
   tool messages, and turn boundaries visible.
2. **Execution trace:** exact recorded message sequences supplied to each model,
   including system instructions, repeated context, summaries, tool interactions,
   retries, and failures. Include harness/internal calls, not just final answers.

LangSmith remains optional observability. Agent Server checkpoints remain responsible
for live execution and resumability. This database is an analysis archive, not a
replacement checkpointer or a promise of deterministic model replay.

## Current integration points

- `backend/app/auth.py` verifies Supabase identity and enforces thread ownership.
- `backend/app/agent.py` builds a LangChain agent with summarization middleware.
- `backend/app/deep_agent.py` builds a Deep Agent with built-in compression and tools.
- `backend/langgraph.json` exposes both graphs through Agent Server.
- The frontend streams runs and uses Agent Server thread history; it does not have
  the authority to choose a recorder owner ID.

Use one shared recording implementation for both agents. Do not duplicate recording
logic or change their response generation just to produce logs.

## Proposed storage

Use a separate database such as `backend/data/chat-recording.sqlite3`, configured by
`CHAT_RECORDING_DB_PATH`. Resolve relative paths against a documented backend base
directory, not an unpredictable process working directory. Keep the database, WAL,
shared-memory files, and attachment directory out of Git.

Enable foreign keys, WAL mode, a busy timeout, and explicit transactions. Choose and
document the synchronous durability setting; start with `FULL` for acknowledged
archive writes. Keep transactions short and never hold them during model/network
calls. Run synchronous SQLite operations outside the async server event loop.

### Schema

Use versioned migrations. Store timestamps in UTC with a consistent, documented
precision, and keep JSON payloads as JSON text with a serialization version.

| Table | Key fields and payload |
| --- | --- |
| `schema_migrations` | Version, application time, migration checksum |
| `installations` | Installation ID, environment, creation time |
| `users` | Installation ID, Supabase project/issuer, verified user ID, optional email snapshot, first/last seen times |
| `conversations` | Internal ID, installation ID, Agent Server thread ID, owner ID, created/updated times, lifecycle status, original metadata JSON |
| `branches` | Branch ID, conversation ID, parent branch, fork message/checkpoint/event reference, creation time |
| `turns` | Turn ID, conversation/branch ID, turn sequence, initiating user ID, accepted/started/finished times, request/idempotency reference, continuation-of turn, status |
| `executions` | Execution ID, turn ID, server run ID, attempt number, graph/assistant ID, parent execution, start/end times, status, error, checkpoint references, trace IDs |
| `messages` | Internal ID, upstream message ID, conversation/branch/turn/execution IDs, conversation and turn sequence numbers, role/type, origin, first observed time |
| `message_revisions` | Revision ID, message ID, revision number, observed/provider timestamps, exact content JSON, raw message JSON, content type, completion state, replacement/removal reference |
| `model_invocations` | Invocation/callback IDs, execution and parent invocation IDs, invocation sequence, provider/model details, generation settings, exact request/response JSON, timing, usage, finish reason, error |
| `invocation_messages` | Model invocation ID, direction, position, message/revision reference when known, exact serialized message snapshot |
| `tool_invocations` | Invocation ID, execution/parent IDs, originating assistant message, tool-call ID, name, raw/parsed arguments, result/error JSON, status, timing, attempt number |
| `tool_message_links` | Tool invocation ID and emitted result-message IDs, supporting multiple outputs and parallel calls |
| `events` | Event ID, conversation event sequence, turn/execution/invocation/message IDs, kind, source event ID, source sequence, occurred/observed times, payload JSON |
| `attachments` | Attachment ID, content hash, MIME type, filename, byte length, durable blob path or inline data, original reference, capture status |
| `message_attachments` | Message revision ID, content-block position, attachment ID |

Common execution metadata must include application Git revision when available,
recorder version, Python/framework/provider package versions, graph name, agent
configuration identity, and frontend renderer version when supplied. Preserve
configuration changes as snapshots rather than changing historical rows.

Index owner/conversation lookup, thread IDs, turn/message/event sequence, time ranges,
run/trace IDs, tool-call IDs, and model names. Add uniqueness constraints for stable
source IDs and sequence allocation. Avoid a global uniqueness assumption for provider
message IDs; scope them to their originating conversation/execution as appropriate.

### Required message and invocation detail

- Preserve role, concrete message type, speaker/name, provider message ID,
  `additional_kwargs`, response metadata, usage metadata, and all structured content
  blocks in their original order.
- Preserve exact text, including Markdown, whitespace, newlines, code fences and
  language labels, links, tables, math, raw HTML text, and Unicode. Do not normalize
  the archive to plain text or store only rendered HTML.
- Store an explicit content-format hint where known. Record renderer/version and
  relevant rendering options if visual reproduction matters. Exact source-content
  reconstruction is required; pixel-identical rendering across UI versions is not.
- Preserve tool-call IDs, names, arguments (including original argument strings and
  invalid/unparseable calls), tool results/artifacts, tool errors, and available
  statuses. Include Deep Agents' built-in planning/filesystem/delegation messages
  whenever they occur, even though these are not the primary use case.
- Capture dynamic system/developer prompts at the effective model boundary after
  middleware transforms. A saved static system-prompt string is insufficient.
- For models, record configured alias, provider-returned model/version if available,
  sampling/token-limit settings, finish reason, token counts, reported cost and its
  source/currency, provider request IDs, and available reasoning/content blocks.
  Private reasoning not exposed by the provider cannot be archived.
- Separate recorder observation time from provider/source time. Capture start, first
  token, last token, and completion times when observable; use a monotonic clock for
  durations within a process.
- Preserve multimodal blocks and attachment bytes where accessible. External or
  temporary URLs alone are insufficient for durable reconstruction; record missing
  bytes as missing rather than silently suggesting the export is complete.
- Preserve custom state/UI/artifact events needed to interpret a turn, without
  assuming every event is itself a chat message.

## Recording lifecycle

1. **Establish trusted context.** At the authenticated request/run boundary, carry the
   verified owner, server thread/run IDs, graph ID, and installation ID into a
   request-scoped recorder context. Never derive ownership from input text, editable
   metadata, a decoded-but-unverified token, or a singleton's mutable user field.
2. **Accept a turn.** Transactionally create/resolve the conversation and branch,
   allocate its next turn sequence, and persist new user input before model work.
   Recognize transport retries through stable server/request IDs where available.
   If a caller intentionally resubmits content, treat it as a new turn.
3. **Capture effective inputs.** At each actual model call, save the full ordered input
   and generation configuration. This includes calls made directly by summarization
   middleware, not only the main agent's model loop.
4. **Capture execution.** Record model and tool start/end/error callbacks with parent
   IDs. Keep parallel tool calls distinct; correlate outputs by tool-call ID rather
   than assuming results complete in request order.
5. **Capture streaming.** Persist ordered text/content/tool-argument deltas in bounded
   batches, then record the finalized message as a separate revision/event. Document
   the possible loss of the last unflushed batch after a crash. Token deltas must not
   each become separate messages in transcript exports.
6. **Finalize.** Record finalized assistant/tool messages, usage, terminal status, and
   timing. Persist a terminal record before acknowledging successful archival
   completion. Distinguish model generation from actual browser delivery; client
   delivery cannot be inferred solely from a model callback.
7. **Handle non-success paths.** Record interruption/resume, timeout, cancellation,
   retry, disconnect, and process failure separately. A disconnect need not mean the
   server run stopped. On restart, reconcile nonterminal executions with Agent Server
   where possible, otherwise mark them interrupted/unknown rather than successful.
8. **Preserve transformations.** Record summarization, message removal, edits, and
   forks as events/revisions. Never erase the original user/assistant content because
   it disappeared from active agent state.

### Ordering, concurrency, and idempotency

- Give turns and logical messages explicit monotonically allocated sequence numbers
  within a conversation. Also retain position within a turn and the active branch.
- Use a transaction to allocate sequences, with database constraints preventing
  duplicates. Initial policy: serialize or reject overlapping turns on the same
  branch, using Agent Server's supported run concurrency policy.
- Event sequence is archive observation order, not proof of causality across parallel
  calls. Preserve source sequence, callback parentage, invocation order, timestamps,
  and branch lineage to reconstruct that distinction.
- Repeated context messages across model calls are input snapshots, not additional
  user submissions. Deduplicate using stable IDs, not content hashes alone: the same
  sentence can legitimately be sent multiple times.
- Assume at-least-once callbacks/delivery and make writes idempotent. SQLite and Agent
  Server checkpoints are separate systems; do not claim cross-system exactly-once
  recording without an outbox/reconciliation mechanism.
- Streaming batches may be retried; event IDs/source sequence must make that safe.
  Preserve separate invocation attempts when the model was actually called again.

## Implementation phases

### 1. Prove the capture boundaries

Inspect the installed LangChain/Deep Agents/Agent Server versions and use small
experiments to establish supported sync and async hooks. Confirm authenticated user,
thread, and run context reaches the recorder without serializing credentials.

Verify whether callbacks inherit into Deep Agents' internal model/tool calls and
summarization. Compare a known test turn against actual model inputs and resulting
state. If standard agent middleware misses accepted input, cancellation, state edits,
or internal calls, add an explicit Agent Server boundary adapter or model callback
adapter. Do not ship incomplete coverage under the label "all messages."

Deliverable: a capture matrix mapping each required record to its hook, metadata
source, ordering guarantee, and known limitation. Confirm middleware ordering before
and after summarization for both agents.

### 2. Build the SQLite repository

Add a shared package such as `backend/app/recording/` with migrations, serialization,
connection/write handling, repositories, and request-scoped context. Use the standard
SQLite library initially unless the async integration experiment justifies another
dependency. Add configuration and ignore rules for DB/blob outputs.

Implement a versioned serializer preserving complete message JSON plus explicit
queryable fields. Preserve unknown extension fields. Put large attachment bytes in
content-addressed files with integrity hashes; commit their references only after
durable writes. Design foreign keys and indexes for eventual PostgreSQL migration.

### 3. Integrate both agents and the server boundary

Add shared middleware/callbacks to both `build_agent()` implementations. Pass trusted
request/run context through without changing prompts, model selection, thread
authorization, or server-managed checkpointing. Support standalone demos with an
explicit local actor identity, clearly distinct from verified Supabase users.

Expose archive-health diagnostics without including message contents in normal
console logs. When recording is enabled, reject a new turn if its initial durable
write fails. Stop further model/tool work after a recording failure where possible,
surface the error, and document that already-sent stream data cannot be recalled.
Do not silently run with an incomplete archive. If recording is explicitly disabled,
make that mode visible and preserve existing application behavior.

### 4. Add reconstruction and export

Provide backend CLI commands for listing conversations, reconstructing a transcript,
and exporting by user, thread, time range, graph, or all users. Cross-user exports are
an operator capability over the local archive; do not weaken the public thread API's
ownership filters or put administrative exports in the ordinary chat UI.

Export a directory/ZIP containing:

- A manifest with schema/export versions, installation ID, filters, UTC time bounds,
  snapshot cutoff, counts, checksums, and completeness/gap information.
- JSONL records for users, conversations, branches, turns, executions, messages and
  revisions, invocation snapshots, tool calls, events, and attachment references.
- Captured attachments with hashes and relative paths.
- A derived chronological transcript per conversation/branch, retaining structured
  data and Markdown source; optional rendered HTML is a convenience view.

Use a consistent database snapshot so concurrent writes cannot produce mismatched
counts or dangling references. Document whether exports include unfinished turns.
Preserve IDs and ordering across export/reimport. Provide example SQL for per-user
conversation counts, turn latency, tool activity, model/token usage, and errors.

### 5. Validate and document operations

Document setup, SQLite path, recording modes, failure behavior, schema upgrades,
consistent backups, attachment handling, export/import, and deletion/retention.
Use SQLite's backup facilities or another consistent snapshot mechanism instead of
copying only the main DB while WAL writes are active.

Keep bearer/refresh tokens, cookies, API keys, and Google client secrets out of raw
request/config dumps. Persist only relevant runtime metadata and record intentional
redaction markers. Any additional content redaction must be documented as a limit on
reconstruction. Restrict operator access to archives and define explicit archive
deletion behavior when a conversation/user is deleted; the immutable event history
does not override an intentional retention/deletion policy.

## Acceptance tests

Use deterministic fake models and tools for repeatable tests; do not require paid
model requests for the main suite.

1. Two verified users create multiple chats across separate login sessions. Ownership,
   user IDs, thread IDs, and messages reconstruct correctly without cross-user leakage.
2. Turns and messages remain ordered after process restart. Timestamps distinguish
   acceptance, generation, observation, and completion; model aliases remain explicit.
3. Markdown with code fences, tables, math, whitespace, links, and Unicode round-trips
   exactly. Structured/multimodal blocks, artifacts, and attachment bytes/hashes survive.
4. A turn with multiple model calls and parallel tools retains every assistant tool
   request, call ID, argument payload, result message, error, and timing relationship.
5. Summarization is triggered in both agents. Original messages remain available, and
   the internal summarization request/response and subsequent model context are saved.
6. Streaming completion, partial output, cancellation, disconnect with continued
   execution, timeout, tool errors, and retry produce distinct, accurate statuses.
7. Duplicate callback delivery and transport retry do not duplicate logical messages;
   intentional repeated messages and real model retries remain distinguishable.
8. Concurrent users and parallel tools do not share request context or corrupt
   sequences. Concurrent turns on one branch follow the configured policy.
9. Edits, removals, thread forks/time travel, and interrupt/resume preserve lineage
   rather than overwriting earlier history or inventing a single linear transcript.
10. DB lock contention, disk-write failure, and an abrupt process stop produce visible
    failures/gap markers. No execution is falsely reported as fully archived.
11. Export during active recording is internally consistent. Reimport into a fresh
    analysis database reproduces message content, metadata, ordering, and relationships.
12. Credentials are absent from stored payloads and exports. Normal users cannot
    access an administrative export through the public API.

## Completion criteria and limits

- Both graphs share the recorder and satisfy the capture matrix and acceptance tests.
- Operators can export all recorded chats for all users and reconstruct transcript and
  execution views without LangSmith access or a running model.
- Previously unrecorded history can only be backfilled from data still present in
  checkpoints or traces. Mark such imports with provenance and unknown/missing fields;
  do not claim to recover already-lost original messages or timing.
- Capturing source messages does not guarantee reproducing the exact UI pixels,
  nondeterministic model behavior, external tool state, or a resumable server session.
- A future PostgreSQL implementation must retain IDs, payload formats, and export
  compatibility; multi-host writes are outside the initial SQLite deployment scope.

## References to verify during implementation

- [LangChain custom middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom)
- [LangChain context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering)
- [Deep Agents context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering)
- [Agent Server authentication and authorization](https://docs.langchain.com/langsmith/auth)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
