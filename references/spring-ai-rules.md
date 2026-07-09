# Spring AI Review Rules

Use this file only when Spring AI, LLM integration, RAG, ChatClient, vector stores, tool calling, MCP, or AI evaluation is in scope.

## Core Review Surface

- Identify Spring AI version, Boot version, model providers, embedding providers, vector stores, advisors, memory, and tool-calling/MCP use.
- Verify provider-specific configuration, API keys, rate limits, timeouts, retries, streaming behavior, and model-specific feature use.
- Treat Spring AI abstractions as portability helpers, not proof that provider behavior, cost, safety, or latency is portable.

## Prompt, Tools, and Safety

- Separate system, developer, retrieved, user, and tool content. Never let retrieved or user-controlled text override tool authorization, data-access policy, or system constraints.
- Treat prompt injection as an application security issue. Review retrieval filters, quoted source handling, tool-use gates, and output validation.
- For tool/function calling, require an allowlist, typed inputs, authorization checks, audit logs, idempotency, timeouts, and dry-run or human approval for destructive or financial actions.
- Validate structured outputs against schemas and business invariants. Do not trust JSON shape alone.
- Do not put secrets, credentials, raw tokens, or sensitive PII into prompts, logs, traces, vector stores, or chat memory.

## RAG and Vector Stores

- Review document ingestion, chunking, embedding model/version, metadata, tenant boundaries, delete/update propagation, and re-indexing strategy.
- Require retrieval evaluation for answer quality, citation accuracy, hallucination rate, and regression after corpus/model changes.
- Verify vector-store filtering and authorization happen before generation, not only after the model answers.
- Track freshness, source attribution, and fallback behavior when retrieval returns no or weak context.

## Operations and Testing

- Track model latency, errors, token usage, cost, rate-limit responses, tool-call counts, retrieval hit rate, and safety-filter outcomes.
- Add tests for prompt templates, structured outputs, tool authorization, retrieval filters, adversarial prompts, provider outages, and vector-store migrations.
- Use representative eval sets before approving production RAG, agentic workflows, or customer-visible autonomous actions.

## Immediate Anti-Patterns

- Tool calling that can mutate state without authorization, idempotency, and audit.
- RAG that retrieves cross-tenant or unauthorized documents.
- Chat memory without retention, deletion, privacy, and PII rules.
- AI output used as a source of truth without validation or human/accountability controls.
