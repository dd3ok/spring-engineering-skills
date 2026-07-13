# Spring AI Review Rules

Use this file only when Spring AI, LLM integration, RAG, ChatClient, vector stores, tool calling, MCP, or AI evaluation is in scope.

## Core Review Surface

- Identify Spring AI version, Boot version, model providers, embedding providers, vector stores, advisors, memory, and tool-calling/MCP use.
- Verify provider-specific configuration, API keys, rate limits, timeouts, retries, streaming behavior, and model-specific feature use.
- Treat Spring AI abstractions as portability helpers, not proof that provider behavior, cost, safety, or latency is portable.

## Execution Model

- Verify the deployed Spring AI line before applying implementation-specific behavior. Distinguish standard/non-streaming calls from streaming, and imperative applications from reactive applications.
- When a model implementation customizes HTTP transport, check whether both `RestClient` and `WebClient` must be configured. Streaming requires the reactive stack, while non-streaming may require the Servlet stack and may block in a reactive application.
- Keep blocking model calls, tool calls, and standard advisor work off WebFlux event-loop threads. Review the configured streaming-advisor scheduler, bounded concurrency, timeouts, cancellation, and context propagation without inventing pool sizes that measurements do not justify.
- Treat tool calling as an imperative workflow on affected versions. Account for partial or interrupted Micrometer observation topology instead of assuming ChatClient and tool-call spans are always connected and complete.

## Prompt, Tools, and Safety

- Separate system, developer, retrieved, user, and tool content. Never let retrieved or user-controlled text override tool authorization, data-access policy, or system constraints.
- Treat prompt injection as an application security issue. Review retrieval filters, quoted source handling, tool-use gates, and output validation.
- Distinguish core MCP support from the separate MCP Security module. Verify the exact module and version; do not present community-driven, work-in-progress security support or its client/server limitations as a generally endorsed production baseline.
- For tool/function calling, require an allowlist, typed inputs, authorization checks, audit logs, idempotency, timeouts, and dry-run or human approval for destructive or financial actions.
- Validate structured outputs against schemas and business invariants. Do not trust JSON shape alone.
- Do not put secrets, credentials, raw tokens, or sensitive PII into prompts, logs, traces, vector stores, or chat memory.
- Define chat-memory retention, deletion, privacy, tenant isolation, and PII handling instead of accepting provider or store defaults.

## RAG and Vector Stores

- Review document ingestion, chunking, embedding model/version, metadata, tenant boundaries, delete/update propagation, and re-indexing strategy.
- Require retrieval evaluation for answer quality, citation accuracy, hallucination rate, and regression after corpus/model changes.
- Verify vector-store filtering and authorization happen before generation, not only after the model answers.
- Track freshness, source attribution, and fallback behavior when retrieval returns no or weak context.

## Operations and Testing

- Track model latency, errors, token usage, cost, rate-limit responses, tool-call counts, retrieval hit rate, and safety-filter outcomes.
- Add tests for prompt templates, structured outputs, tool authorization, retrieval filters, adversarial prompts, provider outages, and vector-store migrations.
- Treat model output as untrusted until application invariants or accountable human review validate it. Use representative eval sets before approving production RAG, agentic workflows, or customer-visible autonomous actions.
