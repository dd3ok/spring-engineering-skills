# Spring Engineering Skills

Spring과 Spring Boot best practice를 근거 기반으로 적용하기 위한 벤더 중립적 **Spring Engineering Skills** 모음입니다. 저장소 검토, 업그레이드 계획, 성능 조사, 위협 모델링, 테스트 공백 분석, Spring Modulith 감사를 지원합니다.

현재 릴리스는 **0.1.0(public beta)**입니다. 스킬 내용과 결정적 스크립트는 [Apache License 2.0](LICENSE)으로 배포합니다.

[English](README.md)

`skills/` 아래에 서로 독립적인 스킬 7개가 있습니다. 각 스킬은 하나의 워크플로만 담당하고 필요한 reference만 선택적으로 읽습니다. 플러그인, 마켓플레이스 manifest, 특정 호스트 전용 metadata 없이 개별 설치할 수 있습니다.

## 이 저장소가 해결하는 문제

Spring 검토에서는 배포 스택을 확인하기 전에 결론을 내리거나, 버전에 민감한 동작을 고정된 출처 없이 설명하거나, 너무 넓은 체크리스트에 중요한 위험이 묻히는 문제가 반복됩니다. 전문 작업까지 하나의 거대한 프롬프트에 넣으면 라우팅도 불명확해집니다.

이 스킬 모음은 다음 원칙으로 이를 방지합니다.

- 결론보다 근거를 먼저 수집합니다.
- 종합 정적 검토와 전문 워크플로의 책임을 분리합니다.
- 스킬별 reference를 필요한 경우에만 읽습니다.
- 업그레이드 주장은 정확한 버전과 출처 provenance를 요구합니다.
- 허용된 출처 publisher만 통과시키는 default-deny 정책을 사용합니다.
- 스키마, validator, 라우팅 계약, 적대적 테스트로 핵심 동작을 고정합니다.
- 저장소 조사와 네트워크 검증에 안전한 기본값을 적용합니다.

## 스킬 구성

| 스킬 | 사용 목적 | 주요 산출물 |
| --- | --- | --- |
| [`spring-evidence-collector`](skills/spring-evidence-collector/) | Spring 빌드, 버전, 설정 키, 소스·테스트 신호, 모듈, 배포 artifact의 읽기 전용·비식별 inventory | 결정적인 `spring-evidence/1` JSON |
| [`spring-upgrade-planner`](skills/spring-upgrade-planner/) | Spring Boot, Spring Cloud, Java/Kotlin, Maven, Gradle의 근거 기반 전환 계획 | 호환성 gate와 rollback을 포함한 `spring-upgrade-plan/2` |
| [`spring-engineering-review`](skills/spring-engineering-review/) | Spring 소스, 설정, 아키텍처, 의존성, 보안, 데이터, 메시징, 운영의 종합 또는 집중 정적 검토 | 근거와 우선순위를 포함한 발견 사항 및 개선안 |
| [`spring-performance-investigator`](skills/spring-performance-investigator/) | JFR, metric, trace, profile, log와 통제 실험을 이용한 인과적 성능 진단 | 우선순위 가설, 확인된 병목, 실험 계획 |
| [`spring-security-threat-modeler`](skills/spring-security-threat-modeler/) | HTTP, reactive, messaging, data, management, outbound 경계의 공격 경로와 잔여 위험 분석 | 위협 목록과 검증 가능한 보안 인수 기준 |
| [`spring-test-gap-planner`](skills/spring-test-gap-planner/) | 운영 위험과 변경 지점을 누락되거나 검증되지 않은 테스트에 연결 | fixture와 CI 위치를 포함한 위험 기반 테스트 공백표 |
| [`spring-modulith-auditor`](skills/spring-modulith-auditor/) | 애플리케이션 모듈 경계, 순환 의존, 내부 API 노출, event, 모듈 테스트, 관측성 감사 | 의존성 위반과 단계별 리팩터링 계획 |

스킬은 서로 보완하지만 대체하지 않습니다. 종합 검토는 정적 위험을 찾고, 전문 스킬은 근거 수집, 업그레이드 계획 작성, 런타임 진단, 위협 모델, 테스트 backlog, 명시적 모듈 graph를 각각 담당합니다.

## 라우팅 원칙

필요한 산출물을 알고 있다면 정확한 스킬 이름으로 요청하는 것이 가장 확실합니다. 각 스킬 frontmatter를 이용한 의미 기반 선택도 가능하지만, 실제 발견·호출 문법은 호스트가 결정합니다.

상위 `spring` dispatcher 스킬은 없습니다. 7개 peer 스킬을 모두 설치하면 이를 지원하는 호스트가 각 스킬의 `name`과 `description`을 보고 암묵적으로 하나를 선택할 수 있습니다. 모호하거나 위험도가 높은 작업처럼 선택을 결정적으로 고정해야 할 때만 정확한 스킬 이름을 사용합니다.

```text
spring-evidence-collector로 이 저장소의 안전한 정적 inventory를 수집해줘.
spring-engineering-review로 이 Spring 서비스의 운영 준비 상태를 검토해줘.
spring-upgrade-planner로 evidence pack 기반의 가역적인 Spring Boot 업그레이드를 계획해줘.
spring-performance-investigator로 이 JFR과 Micrometer 지연을 연관 분석해줘.
spring-security-threat-modeler로 이 멀티테넌트 API의 신뢰 경계를 모델링해줘.
spring-test-gap-planner로 장애 모드를 위험 기반 테스트 backlog로 변환해줘.
spring-modulith-auditor로 ApplicationModules 경계와 순환 의존을 감사해줘.
```

일반적인 Spring 개념 설명, 단일 실패 테스트 수정, CVE 조회, 능동 침투 테스트, 무관한 아키텍처 의사결정에는 이 스킬들을 자동 활성화하지 않습니다. [`evals/`](evals/)의 라우팅 계약이 활성·비활성 경계를 함께 고정합니다.

## 설치

저장소를 복제합니다.

```text
git clone https://github.com/dd3ok/spring-engineering-skills.git
```

스킬 하나를 설치하려면 `skills/<skill-name>/` 전체를 대상 호스트가 지원하는 스킬 위치로 복사합니다. 전체 모음을 설치하려면 7개 디렉터리를 모두 복사합니다. 각 스킬의 `SKILL.md`, `references/`, 선택적 `scripts/`는 분리하지 않습니다.

Codex에서는 저장소별 발견에 `.agents/skills/`, 사용자 전체 발견에 `$HOME/.agents/skills/`를 사용합니다. 7개 스킬을 모두 설치하면 Codex가 metadata를 보고 적합한 peer 스킬을 암묵적으로 선택할 수 있습니다. 이 설치 방식은 벤더 중립적인 스킬 내용 자체를 변경하지 않습니다. 자세한 내용은 [Codex skills 문서](https://learn.chatgpt.com/docs/customization/overview#skills)를 참고합니다.

플러그인은 필요하지 않습니다. portable source contract에는 플러그인 manifest, marketplace metadata, 생성된 벤더 package, 호스트 전용 agent 설정을 포함하지 않습니다.

## 근거 우선 워크플로

종합 검토와 업그레이드는 정적 근거 수집부터 시작하는 것을 권장합니다.

```text
python skills/spring-evidence-collector/scripts/collect_evidence.py <repository> --output evidence.json
python skills/spring-evidence-collector/scripts/validate_evidence.py evidence.json
```

정적 수집은 빌드를 실행하거나 의존성을 resolve하거나 네트워크를 호출하지 않습니다. Maven 상속·profile, 실행 가능한 Gradle 로직과 같은 effective state는 별도로 허가된 환경에서 생성하고 구조화된 provenance를 포함한 resolved report로 가져와야 합니다.

Evidence pack과 정확한 대상 버전으로 업그레이드 계획 초안을 만들고 검증합니다.

```text
python skills/spring-upgrade-planner/scripts/build_plan_skeleton.py evidence.json --target 4.1.0 --output upgrade-plan.json
python skills/spring-upgrade-planner/scripts/validate_upgrade_plan.py upgrade-plan.json
```

대상은 정확한 버전이어야 하며 `latest`는 지원하지 않습니다. 공식 지원 정책, 호환성, migration, 검증, rollback, freshness, 내용 주소 기반 출처가 ready 계약을 충족하기 전까지 계획은 `draft` 상태로 유지됩니다. prerelease와 downgrade는 명시적으로 허용해야 합니다.

## 안전성과 근거 보장

- 저장소 내용은 지시가 아니라 신뢰할 수 없는 데이터로 취급합니다.
- 정적 수집은 읽기 전용이며 결정적으로 동작해야 합니다.
- 파일 이름이 secret 가능성을 나타내는 설정 파일은 열지 않습니다.
- 설정 값이 아니라 설정 키와 구조만 기록합니다.
- 정적 근거의 certainty는 `declared` 또는 `inferred`로 제한하고, 완전한 provenance와 sanitization metadata가 있는 imported evidence에만 `resolved`를 허용합니다.
- 입력 크기를 제한하고 잘못된 데이터는 crash 대신 검증 오류로 반환합니다.
- ready 업그레이드 계획을 정확한 evidence snapshot, canonical fact ID, source locator, hash, 수집 시각, project identity에 연결합니다.
- 공식 framework, platform, specification, project 출처를 우선합니다. GitHub 출처는 승인된 owner만 허용합니다.
- private·non-global 링크 목적지, HTTPS에서 HTTP로의 downgrade, 안전하지 않은 redirect, 승인되지 않은 publisher를 기본 차단합니다.

세부 규칙은 각 스킬의 reference에 있으며 필요한 경우에만 읽습니다.

## 저장소 구조

```text
skills/
  <skill-name>/
    SKILL.md             # 활성화 metadata와 핵심 워크플로
    references/          # 규칙, playbook, schema, 공식 출처 map
    scripts/             # 필요한 경우의 결정적 자동화
evals/
  routing-cases.json
  review-routing-policy.json
  behavior-cases.json
  source-publisher-policy.json
scripts/                 # 저장소 전체 validator
tests/                   # 단위, 계약, 보안, 적대적 테스트
```

결정적 스크립트는 Python 3.12 이상이 필요하며 Python 표준 라이브러리만 사용합니다.

## 호환성과 버전 정책

| 구분 | 현재 계약 |
| --- | --- |
| 스킬 모음 릴리스 | `0.1.0` (public beta) |
| 스킬 형식 | [Agent Skills specification](https://agentskills.io/specification) |
| 결정적 스크립트 | Python 3.12 이상 |
| Evidence artifact | `spring-evidence/1` |
| Upgrade-plan artifact | `spring-upgrade-plan/2` |

`1.0.0` 전에는 라우팅 근거나 안전 요구사항에 따라 스킬 이름과 schema가 바뀔 수 있습니다. 이 시기의 호환성 변경은 minor, 수정은 patch 버전을 올립니다. `1.0.0`부터는 공개 계약을 깨는 변경은 major, 하위 호환 기능은 minor 버전을 올립니다.

## 검증

전체 오프라인 검증을 실행합니다.

```text
python scripts/validate_all.py
```

다음을 검사합니다.

- 7개 스킬의 구조와 frontmatter
- 승인된 source publisher registry와 스킬별 source map
- 정확한 라우팅·reference 분할과 behavior case 계약
- evidence 및 upgrade schema 의미 규칙
- malformed, oversized, stale, future-dated, secret-bearing, 적대적 입력
- 저장소에 포함된 Maven reactor 및 Gradle Groovy/Kotlin 멀티프로젝트 evidence fixture
- 전체 단위 테스트
- 내부 Markdown 링크

GitHub Actions의 [`validate`](.github/workflows/validate.yml) workflow는 pull request와 `main` push에서 이 오프라인 검사와 고정 버전 Ruff를 실행합니다. 기본 브랜치에서 workflow가 한 번 실행된 후 `validate` job을 branch protection의 필수 체크로 지정합니다.

외부 출처는 별도로 검사합니다.

```text
python scripts/check_links.py --online --retries 2 --json-report dist/link-report.json
```

온라인 검사는 제한된 재시도, 검증된 목적지 고정, redirect 제한과 명시적인 `ok`, `inconclusive`, `failed` 결과를 사용합니다. 원격 가용성은 재현 가능하지 않으므로 결정적인 오프라인 검사와 분리합니다.

## 평가 범위

[`evals/routing-cases.json`](evals/routing-cases.json)은 라우팅 명세의 내부 일관성을 검증하지만 특정 모델이나 호스트가 실제 프롬프트를 어떻게 선택할지는 보장하지 않습니다. [`evals/behavior-cases.json`](evals/behavior-cases.json)은 blind forward test용 프롬프트와 부모 측 rubric을 제공합니다. 한 번의 성공은 smoke test이지 통계적 품질 보장이 아닙니다.

실제 호스트·모델의 라우팅을 측정하려면 기대값이 제거된 프롬프트를 내보내고 관측된 선택 결과를 채점합니다.

```text
python scripts/score_routing_results.py --emit-prompts dist/routing-prompts.jsonl
python scripts/score_routing_results.py dist/routing-results.jsonl --json-report dist/routing-report.json
```

평가 절차와 한계는 [`evals/README.md`](evals/README.md)를 참고합니다.

## 현재 설계

이 저장소는 하나의 거대한 스킬에서 portable suite로 전환됐습니다.

- root의 스킬 내용을 `skills/` 아래로 옮기고 책임이 분명한 7개 워크플로로 분리했습니다.
- 종합 검토 reference를 web, HTTP client, data, messaging, security, scheduling, performance, operations, Spring AI, Spring Batch, API protocol, migration 관심사로 나눴습니다.
- evidence와 upgrade artifact에 versioned schema, semantic validator, provenance, freshness, snapshot binding을 추가했습니다.
- Gradle·Maven topology, secret-file 경계, malformed input, 링크 재시도·redirect 동작을 회귀 테스트로 고정했습니다.
- 라우팅, behavior, 출처 신뢰, publisher ownership을 기계 검증 가능한 계약으로 만들었습니다.
- portable source tree에서 플러그인과 벤더 배포 의존성을 제거했습니다.

## 기여 원칙

`SKILL.md`는 간결하고 절차 중심으로 유지합니다. 상세 규칙, schema, 버전 민감 정보는 스킬별 `references/`에 두고, 반복 가능성이나 안전성을 위해 필요한 경우에만 결정적 스크립트를 추가합니다. 새로운 route, 조건부 reference, publisher, schema field, failure mode에는 대응하는 계약 또는 회귀 테스트가 있어야 합니다.

변경을 제안하기 전에 다음을 실행합니다.

```text
python scripts/validate_all.py
python scripts/check_links.py --online --retries 2
```

저장소 구조는 [Agent Skills specification](https://agentskills.io/specification)을 따릅니다.

## 라이선스

[Apache License 2.0](LICENSE)을 적용합니다. 현재 `NOTICE` 파일은 없으며, 향후 보존해야 할 제3자 고지가 도입되면 함께 유지합니다.
