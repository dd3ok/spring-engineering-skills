# Spring Best Practice Skill

[English README](README.md)

Codex, Claude Code, Antigravity 같은 Agent Skills 클라이언트에서 쓸 수 있는 Spring Boot 리뷰 스킬입니다.

AI 코딩 에이전트가 Spring 또는 Spring Boot 시스템을 리뷰할 때 쓰도록 만들었습니다. 아키텍처, 운영 준비도, 의존성 선택, 마이그레이션, 보안, 데이터 접근, 메시징, 배치, Spring AI, HTTP 클라이언트, API 프로토콜, 배포 리스크를 finding-first 방식으로 점검합니다.

## 언제 쓰나

잘 맞는 요청:

- Spring Boot 서비스를 운영 배포 전에 점검할 때
- Spring 아키텍처, 모듈 경계, 설정, 의존성 선택을 리뷰할 때
- 보안, 관측성, 트랜잭션, HTTP 클라이언트, 캐시, 메시징, 스케줄링, 배치, 데이터 접근 리스크를 확인할 때
- Spring AI, RAG, ChatClient, vector store, tool calling, model provider 장애 모드를 검토할 때
- Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Java, Kotlin, Jakarta, Maven, Gradle 관련 주요 버전 업그레이드를 준비할 때
- 아키텍처 제안, 마이그레이션 계획, 운영 준비도 주장을 검증하고 싶을 때

맞지 않는 요청:

- `@Transactional`이 무엇인지 묻는 기본 Spring 질문
- Spring 맥락이 없는 일반 Java 질문
- 리뷰할 코드, 의존성, 설계, 운영 조건 없이 권장 방식만 넓게 요약해 달라는 요청

## 리뷰 방식

스킬은 먼저 `SKILL.md`를 읽고, 요청에 필요한 reference만 추가로 엽니다. 리뷰 결과는 넓은 조언보다 구체적인 finding, 심각도, 근거, 영향을 받는 파일이나 컴포넌트를 먼저 보여주는 형식을 따릅니다.

기본 출력 형태:

```markdown
## Findings
## Verdict
## Evidence
## Recommendations
## Tests
## Operations
## Open Questions
```

입력이 부족하면 보수적인 가정을 명시하고 진행합니다. 모르는 사실을 만들어내지 않습니다. 최근 버전이나 버전별 동작을 말해야 할 때는 공식 Spring 문서를 확인하는 쪽을 기본으로 둡니다.

## 리뷰 범위

| 리뷰 대상 | Reference |
| --- | --- |
| Spring/Spring Boot 핵심 아키텍처, 운영 준비도, 보안, 관측성, 트랜잭션 | `references/review-rules.md` |
| 주요 버전 업그레이드와 의존성 호환성 | `references/migration-rules.md` |
| HTTP 클라이언트, 서비스 간 deadline, retry, pool, SSRF | `references/http-client-rules.md` |
| Redis cache, lock, topology, session, rate limiting, stream, pub/sub | `references/redis-rules.md` |
| 스케줄링, `@Scheduled`, Quartz, async executor, overlap, virtual-thread scheduling | `references/scheduling-rules.md` |
| Spring AI, LLM/RAG, ChatClient, vector store, tool calling, MCP, evaluation | `references/spring-ai-rules.md` |
| Spring Batch, restartability, partitioning, chunk processing | `references/spring-batch-rules.md` |
| RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, JMS | `references/messaging-rules.md` |
| GraphQL, gRPC, Authorization Server, Session, HATEOAS, SOAP/Web Services, LDAP | `references/api-protocol-rules.md` |
| jOOQ, NoSQL, Spring Data REST, JPA/JDBC/R2DBC 바깥의 data-access 전략 | `references/data-access-rules.md` |
| 버전별 주장에 필요한 공식 문서 링크 | `references/official-docs.md` |
| 패키징과 런타임 호환성 | `references/vendor-compatibility.md` |

## 빠른 시작

Codex/OpenAI:

```text
$spring-best-practice-skill review this Spring Boot service for production readiness.
```

Claude Code:

```text
/spring-best-practice-skill review the Redis cache and lock design in this project.
```

이 스킬은 명시적으로 호출해서 쓰는 쪽을 기준으로 설계했습니다. Codex에서는 `agents/openai.yaml`에 `policy.allow_implicit_invocation: false`가 들어 있어, 일반 Spring 프롬프트만으로는 이 리뷰 워크플로가 자동 호출되지 않도록 맞춰져 있습니다.

## 설치

### Codex/OpenAI

특정 저장소에서만 쓰려면 이 폴더를 다음 위치에 둡니다.

```text
<repo>/.agents/skills/spring-best-practice-skill/
```

개인 환경 전체에서 쓰려면 다음 위치에 둡니다.

```text
$HOME/.agents/skills/spring-best-practice-skill/
```

Codex는 보통 skill 변경을 자동으로 감지합니다. 목록에 보이지 않으면 Codex를 재시작하세요.

### Claude Code

다음 중 하나에 설치합니다.

```text
~/.claude/skills/spring-best-practice-skill/
<repo>/.claude/skills/spring-best-practice-skill/
```

공용 `SKILL.md`는 여러 런타임에서 읽을 수 있는 형식을 유지하므로 Claude 전용 frontmatter를 넣지 않습니다. Claude 전용 manual-only 패키지가 필요하면 아래 명령으로 생성하고 검증합니다.

```powershell
python scripts/build_claude_package.py
python scripts/validate_claude_package.py
```

Claude 전용 배포에는 생성된 `dist/claude/` 결과물을 사용합니다.

### Antigravity

먼저 프로젝트 범위 설치를 권장합니다.

```text
<project-root>/.agents/skills/spring-best-practice-skill/
```

Antigravity와 Antigravity CLI는 스킬 검색 방식이 다를 수 있습니다. 전역 경로나 별칭을 문서화하기 전에, 실제 대상 런타임에서 설치 경로와 호출 동작을 확인하세요.

## 패키지 구조

```text
spring-best-practice-skill/
|-- SKILL.md
|-- README.md
|-- README.ko.md
|-- agents/
|   `-- openai.yaml
|-- scripts/
|   |-- build_claude_package.py
|   `-- validate_claude_package.py
`-- references/
    |-- api-protocol-rules.md
    |-- data-access-rules.md
    |-- http-client-rules.md
    |-- messaging-rules.md
    |-- migration-rules.md
    |-- official-docs.md
    |-- redis-rules.md
    |-- review-rules.md
    |-- scheduling-rules.md
    |-- spring-ai-rules.md
    |-- spring-batch-rules.md
    `-- vendor-compatibility.md
```

`dist/claude/`는 생성물입니다. 직접 수정하지 않습니다.

## 추가 예시

아키텍처 리뷰:

```text
$spring-best-practice-skill review this migration plan from Spring Boot 3.5 to 4.x. Focus on dependency compatibility, Jakarta changes, security behavior, and rollout risk.
```

Spring AI 리뷰:

```text
$spring-best-practice-skill review this Spring AI RAG design. Check retrieval boundaries, tool calling safety, evaluation coverage, and model-provider failure modes.
```

HTTP 클라이언트 리뷰:

```text
$spring-best-practice-skill review our RestClient/WebClient timeout, retry, and SSRF posture.
```

## 검증

Codex skill 구조 검증을 실행합니다.

```powershell
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" .
```

기대 결과:

```text
Skill is valid!
```

기본 유지보수 체크:

```powershell
git diff --check
```

Claude 배포본을 준비할 때만 아래 명령을 실행합니다.

```powershell
python scripts/build_claude_package.py
python scripts/validate_claude_package.py
```

기대 결과:

```text
Claude package is valid!
```

`dist/claude/`에는 Claude 전용 frontmatter가 들어가므로 Codex `quick_validate.py`를 돌리지 않습니다.

## 릴리스 체크리스트

- `SKILL.md` frontmatter는 여러 런타임에서 읽을 수 있는 형태로 유지합니다.
- 일반 Spring 질문에 우연히 켜지지 않도록 description 범위를 좁게 유지합니다.
- `agents/openai.yaml`의 `policy.allow_implicit_invocation: false`를 확인합니다.
- `quick_validate.py`를 실행합니다.
- `git diff --check`를 실행합니다.
- Claude 전용 배포가 필요할 때만 `dist/claude/`를 다시 만들고 검증합니다.
- 각 대상 런타임에서 명시적 호출을 smoke test한 뒤 사용법을 배포 문서에 적습니다.
- activation policy, 설치 경로, vendor-specific metadata를 바꾸기 전에는 `references/vendor-compatibility.md`를 확인합니다.

## 참고 문서

- [OpenAI Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Claude Code skills documentation](https://code.claude.com/docs/en/skills)
- [Anthropic Agent Skills overview](https://console.anthropic.com/docs/en/agents-and-tools/agent-skills/overview)
- [Google Antigravity skills authoring codelab](https://codelabs.developers.google.com/getting-started-google-antigravity)
- [Google Antigravity CLI skills codelab](https://codelabs.developers.google.com/antigravity/how-to-create-agent-skills-for-antigravity-cli)
