# Spring Engineering Skills

Spring 엔지니어링 작업을 위한 벤더 중립·근거 중심 Agent Skills 모음입니다. `skills/` 아래의 각 디렉터리는 자체 참조 문서와 스크립트만 사용하는 독립적인 스킬입니다.

## 스킬 구성

| 스킬 | 역할 | 주요 산출물 |
| --- | --- | --- |
| `spring-evidence-collector` | 읽기 전용·비식별 저장소 인벤토리 | 결정적인 `spring-evidence/1` JSON |
| `spring-upgrade-planner` | Spring·Java·빌드 도구 전환 계획 | 호환성 게이트와 단계별 전환안 |
| `spring-best-practice-review` | Spring 정적 종합·집중 검토 | 근거와 신뢰도를 포함한 개선 항목 |
| `spring-performance-investigator` | 런타임 성능 진단 | 우선순위 가설, 확인된 병목, 통제 실험 |
| `spring-security-threat-modeler` | 신뢰 경계·공격 경로 분석 | 위협 목록과 검증 가능한 보안 인수 기준 |
| `spring-test-gap-planner` | 위험 대비 테스트 근거 분석 | 우선순위 테스트 공백 목록 |
| `spring-modulith-auditor` | 애플리케이션 모듈 경계 감사 | 의존성 위반과 리팩터링 단계 |

각 스킬은 서로 다른 깊이와 최종 산출물을 소유합니다. 종합 검토 스킬은 정적 설계 위험을 찾고, 전용 스킬은 증거 수집·업그레이드 계획·런타임 진단·위협 모델·테스트 백로그·모듈 그래프를 담당합니다.

## 구조

```text
skills/<skill-name>/
  SKILL.md
  references/
  scripts/              # 결정적 자동화가 필요한 경우에만 포함
evals/
scripts/
tests/
```

플러그인 manifest, marketplace metadata, 호스트 전용 agent metadata, 벤더별 생성 패키지는 소스 계약에 포함하지 않습니다.

## 사용

대상 호스트가 지원하는 스킬 선택 방법을 사용하거나 정확한 스킬 이름으로 요청합니다. 발견·호출 문법은 호스트의 책임이며 스킬 본문에는 특정 벤더 문법을 넣지 않습니다.

```text
spring-evidence-collector로 이 저장소의 안전한 인벤토리를 수집해줘.
spring-upgrade-planner로 Spring Boot 3.5에서 4.1 전환 계획을 세워줘.
spring-best-practice-review로 이 서비스를 운영 준비 관점에서 검토해줘.
```

개별 스킬을 설치할 때는 `skills/<skill-name>/` 전체를 대상 호스트가 지원하는 스킬 위치에 복사합니다. `SKILL.md`, `references/`, `scripts/`를 서로 다른 위치로 나누지 않습니다.

## Python 런타임

결정적 스크립트에는 Python 3.12 이상이 필요하며 표준 라이브러리만 사용합니다.

## 증거 수집

기본 수집은 빌드나 네트워크 요청을 실행하지 않고 설정값을 출력하지 않습니다.

```text
python skills/spring-evidence-collector/scripts/collect_evidence.py <repository> --output evidence.json
python skills/spring-evidence-collector/scripts/validate_evidence.py evidence.json
```

Maven 상속·프로필과 실행 가능한 Gradle 로직에는 별도로 통제된 환경에서 생성한 effective/resolved 보고서가 필요합니다. 정적 선언은 `declared` 또는 `inferred`로 유지합니다.

## 업그레이드 계획

증거 파일과 정확한 대상 버전으로 결정적인 초안을 만듭니다.

```text
python skills/spring-upgrade-planner/scripts/build_plan_skeleton.py evidence.json --target 4.1.0 --output upgrade-plan.json
python skills/spring-upgrade-planner/scripts/validate_upgrade_plan.py upgrade-plan.json
```

공식 지원·호환성·마이그레이션·검증·롤백과 내용 주소 기반 출처 근거가 연결되기 전까지 계획은 `draft` 상태를 유지합니다. 고정한 메타데이터 없이 `latest`를 추측하지 않으며 다운그레이드는 명시적으로 허용해야 합니다.

## 검증

```text
python scripts/validate_all.py
```

이 벤더 중립 명령은 스킬 구조와 출처 정책, 라우팅과 행위 계약, 전체 단위 테스트, 오프라인 링크를 검사합니다. 실패 원인을 좁힐 때는 `scripts/` 아래의 개별 검증기를 실행합니다.

외부 출처는 별도 네트워크 작업으로 검사할 수 있습니다.

```text
python scripts/check_links.py --online --json-report dist/link-report.json
```

## 출처 정책

버전에 민감한 주장은 다시 확인합니다. Spring과 관련 프로젝트의 공식 문서·릴리스 노트·마이그레이션 가이드·BOM·명세·저장소를 우선하고, 논문과 주요 기술 조직의 문서는 보조 근거로 사용합니다. 기술 블로그 하나만으로 프레임워크 동작을 확정하지 않습니다.

저장소 구조는 [Agent Skills 명세](https://agentskills.io/specification)를 따릅니다. 각 스킬이 독립적으로 이동할 수 있도록 기술 출처 맵도 스킬 내부에 둡니다. 행위 프롬프트와 블라인드 순방향 테스트 방법은 [evals/README.md](evals/README.md)에 정리되어 있습니다.

## 기존 단일 스킬에서 전환

- 루트의 종합 검토 스킬은 `skills/spring-best-practice-review/`로 이동했습니다.
- 전문 워크플로는 `skills/` 아래의 형제 스킬로 분리했습니다.
- 호스트 전용 플러그인·마켓플레이스·agent metadata는 의도적으로 지원하지 않습니다.
