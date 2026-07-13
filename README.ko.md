# Spring Engineering Skills

Spring과 Spring Boot 엔지니어링을 위한, 특정 벤더에 종속되지 않는 [Agent Skills](https://agentskills.io/specification) 모음입니다. 하나의 거대한 스킬 대신 코드 리뷰, 저장소 근거 수집, 업그레이드, 성능, 보안, 테스트, Modulith 경계를 각각 독립된 스킬로 제공합니다.

[![GitHub Release](https://img.shields.io/github/v/release/dd3ok/spring-engineering-skills)](https://github.com/dd3ok/spring-engineering-skills/releases/latest)
[![Validate](https://github.com/dd3ok/spring-engineering-skills/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/dd3ok/spring-engineering-skills/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/dd3ok/spring-engineering-skills)](LICENSE)

[English](README.md) · [변경 이력](CHANGELOG.md)

## 설계 원칙

- **명확한 책임** — 각 스킬은 하나의 워크플로와 주 산출물을 담당합니다.
- **근거 우선** — 관찰된 사실, 추론, 확인하지 못한 항목을 구분합니다.
- **버전 인식** — 호환성과 마이그레이션 판단에는 정확한 대상 버전과 검토된 출처를 요구합니다.
- **단계적 공개** — 핵심 절차를 먼저 읽고 작업에 필요한 reference만 추가로 사용합니다.
- **안전한 자동화** — 결정적 스크립트는 범위가 제한되며 저장소 빌드를 임의로 실행하지 않습니다.

## 스킬 선택

| 스킬 | 사용 목적 | 주 산출물 |
| --- | --- | --- |
| [`spring-engineering-review`](skills/spring-engineering-review/) | Spring/Spring Boot 코드, 설정, 의존성, 아키텍처, 보안, 데이터, 메시징, 운영 준비 상태의 정적 검토 | 근거와 우선순위가 있는 발견 사항 및 개선안 |
| [`spring-evidence-collector`](skills/spring-evidence-collector/) | 빌드 파일, 버전, 설정 키, 모듈, 소스·테스트 신호, 배포 artifact의 읽기 전용·비식별 수집 | 결정적인 `spring-evidence/1` JSON |
| [`spring-upgrade-planner`](skills/spring-upgrade-planner/) | Spring Boot, Spring Cloud, Java/Kotlin, Maven, Gradle의 근거 기반 업그레이드 계획 | 검증 단계와 rollback을 포함한 `spring-upgrade-plan/2` |
| [`spring-performance-investigator`](skills/spring-performance-investigator/) | JFR, metric, trace, profile, log와 통제된 실험을 이용한 성능 진단 | 우선순위가 있는 가설과 확인된 병목 |
| [`spring-security-threat-modeler`](skills/spring-security-threat-modeler/) | HTTP, reactive, messaging, data, management, outbound 영역의 신뢰 경계와 공격 경로 분석 | 위협 목록과 검증 가능한 보안 기준 |
| [`spring-test-gap-planner`](skills/spring-test-gap-planner/) | 운영 위험과 변경 신호를 누락된 테스트에 연결 | 우선순위가 있는 테스트 공백 목록 |
| [`spring-modulith-auditor`](skills/spring-modulith-auditor/) | 애플리케이션 모듈 경계, 순환 의존성, 내부 API 노출, event, module test, 관측성 점검 | 경계 위반과 단계별 리팩터링 계획 |

스킬은 상하 관계가 없는 독립적인 구성입니다. 필요한 스킬만 설치하면 호환되는 호스트가 `name`과 `description`을 바탕으로 하나를 선택할 수 있습니다. 요청이 모호하거나 선택 결과를 고정해야 할 때는 정확한 스킬 이름을 사용하세요.

## 산출물 동작 방식

7개 스킬 모두 구조화된 결과를 에이전트의 일반 응답으로 반환합니다. 스킬이 활성화되었다는 이유만으로 작업 공간에 파일을 작성하지는 않습니다.

다음 두 스킬만 버전이 지정된 공식 JSON artifact와 validator를 추가로 제공합니다.

- `spring-evidence-collector`는 검증된 동일 입력을 다른 검토나 계획에서 재사용할 수 있도록, 비식별 저장소 사실을 `spring-evidence/1` 형식으로 저장할 수 있습니다.
- `spring-upgrade-planner`는 근거 연결, 작업 단계, 호환성 gate, 검증, rollback을 일관되게 검사할 수 있도록 `spring-upgrade-plan/2` 형식으로 저장할 수 있습니다.

나머지 5개 스킬은 요청과 근거에 따라 달라지는 발견 사항, 가설, 위협 모델, 테스트 matrix, 감사 결과를 만듭니다. 여기에 고정된 파일 schema를 강제하면 불필요하게 경직되고 무거워집니다. 요청하면 Markdown이나 JSON으로 저장할 수 있지만, 기본적으로 공식 artifact를 생성하지는 않습니다.

## 빠른 시작

저장소를 복제합니다.

```text
git clone https://github.com/dd3ok/spring-engineering-skills.git
```

스킬 하나를 설치하려면 `skills/<skill-name>/` 전체를 host가 지원하는 스킬 경로로 복사합니다. `SKILL.md`, `LICENSE`, `references/`, 선택 사항인 `scripts/`를 함께 유지하세요. 전체 모음을 설치하려면 7개 스킬 디렉터리를 모두 복사합니다.

요청 예시:

```text
spring-engineering-review로 이 Spring Boot 서비스의 운영 준비 상태를 검토해줘.
spring-evidence-collector로 이 저장소의 비식별 정적 근거를 수집해줘.
spring-upgrade-planner로 Spring Boot 3.5에서 4.1로의 근거 기반 업그레이드를 계획해줘.
spring-performance-investigator로 이 JFR과 Micrometer 자료를 분석해줘.
```

일반적인 Spring 질문, 단일 코드 수정, CVE 조회, 범위가 정해지지 않은 아키텍처 논의에는 이 스킬 모음을 자동으로 활성화하지 않는 것이 좋습니다.

## 근거 우선 워크플로

저장소 전체 검토나 업그레이드는 정적 근거 수집부터 시작합니다.

```text
python skills/spring-evidence-collector/scripts/collect_evidence.py <repository> --output evidence.json
python skills/spring-evidence-collector/scripts/validate_evidence.py evidence.json
```

collector는 Maven이나 Gradle을 실행하거나, 의존성을 resolve하거나, 네트워크에 접근하거나, 설정 값을 출력하지 않습니다. 실행 가능한 빌드 로직과 실제 의존성 상태는 통제된 환경에서 별도로 승인받아 수집해야 합니다.

파일 형태의 인계 자료가 필요할 때 collector와 planner는 서로 다른 기계 판독용 JSON artifact를 생성합니다.

| 파일 | 생성 스킬 | 역할 |
| --- | --- | --- |
| `evidence.json` | `spring-evidence-collector` | 이후 검토와 계획에서 사용할 저장소 사실을 기록합니다. |
| `upgrade-plan.json` | `spring-upgrade-planner` | `evidence.json`과 정확한 대상 버전을 입력으로 단계별 업그레이드 초안을 만듭니다. |

planner는 evidence 파일을 읽지만 덮어쓰지는 않습니다. 두 파일은 일반 문서가 아닌 구조화된 artifact이며, 스킬이 선택되었다는 이유만으로 자동 저장되지 않습니다. 필요하면 에이전트에게 Markdown 요약을 별도로 요청할 수 있습니다.

수집한 근거로 업그레이드 계획 초안을 만들고 검증합니다.

```text
python skills/spring-upgrade-planner/scripts/build_plan_skeleton.py evidence.json --target 4.1.0 --output upgrade-plan.json
python skills/spring-upgrade-planner/scripts/validate_upgrade_plan.py upgrade-plan.json
```

대상은 정확한 버전이어야 합니다. 호환성, 마이그레이션, 검증, rollback, freshness, 내용 주소 기반 출처가 ready 조건을 충족하기 전까지 계획은 `draft`로 유지됩니다.

## 저장소 검증

결정적 스크립트는 Python 3.12 이상과 표준 라이브러리만 사용합니다.

```text
python scripts/validate_all.py
```

스킬 구조와 경로, reference, 출처 정책, 라우팅과 동작 계약, schema, 단위 테스트, golden repository fixture, 오프라인 링크를 검사합니다. CI에서는 Ruff와 Windows junction smoke test도 실행합니다.

네트워크가 필요한 freshness 검사는 pull request 필수 검증과 분리되어 있습니다.

```text
python scripts/check_spring_cloud_policy.py --online
python scripts/check_links.py --online --json-report dist/link-report.json
```

라우팅 case는 저장소 계약을 검증할 뿐, 특정 host의 실제 자동 활성화를 보장하지 않습니다. 반복 host trace와 blind behavior 평가 방법은 [`evals/README.md`](evals/README.md)에 설명되어 있습니다.

## 저장소 구조

```text
skills/       독립적으로 설치할 수 있는 스킬
evals/        라우팅, 동작, 출처 정책 계약
scripts/      저장소 전체 validator와 scorer
tests/        단위, 적대적, 이식성, golden fixture 테스트
```

상세한 Spring 규칙, schema, 출처 map은 이를 담당하는 스킬 안에 둡니다. portable source tree에는 plugin manifest, marketplace package, host 전용 agent 설정이 없습니다.

## 호환성

| 계약 | 현재 값 |
| --- | --- |
| 스킬 형식 | [Agent Skills 공개 표준 명세](https://agentskills.io/specification) |
| 결정적 스크립트 | Python 3.12+ |
| Evidence artifact | `spring-evidence/1` |
| Upgrade-plan artifact | `spring-upgrade-plan/2` |
| Routing report | `spring-routing-eval/2` |

### 안정화 계약과 버전 정책

`1.0.0`은 공개 계약을 호환성 있게 유지하겠다는 선언이며, 모든 기능이 완성되었다는 의미는 아닙니다. 공개 계약의 범위는 다음과 같습니다.

- 배포된 7개 스킬의 이름, 활성화 경계, 담당 산출물
- evidence, upgrade-plan, routing-report의 버전 지정 schema
- 결정적 스크립트의 CLI와 기본 출력 동작, Python 기준 버전, 이식 가능한 스킬 구조

호환성을 유지하는 기능 추가는 minor 버전, 호환되는 수정은 patch 버전, 공개 계약을 깨는 변경은 major 버전을 올립니다. 릴리스별 변경 사항은 [변경 이력](CHANGELOG.md)을 참고하세요.

## 기여

`SKILL.md`는 간결한 절차 중심으로 유지합니다. 상세 규칙과 출처는 목적이 분명한 `references/` 파일에 두고, 안전성이나 반복 가능성을 실질적으로 높일 때만 스크립트를 추가합니다. 새로운 route, schema, source publisher, failure mode에는 대응하는 계약 또는 회귀 테스트가 필요합니다.

pull request를 열기 전에 실행하세요.

```text
python scripts/validate_all.py
python -m ruff check scripts tests skills
```

## 라이선스

[Apache License 2.0](LICENSE)을 적용합니다. 독립적으로 배포할 수 있는 각 스킬에도 같은 라이선스 파일이 포함되어 있습니다.
