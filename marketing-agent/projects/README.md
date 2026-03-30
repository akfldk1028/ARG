# projects/ — 프로젝트 설정 가이드

이 폴더에 YAML 파일 하나를 넣으면 marketing-agent가 해당 제품의 마케팅을 자동 실행합니다.

## 빠른 시작

```bash
cp _template.yaml my-product.yaml
# 필드 채우기 → 끝
```

## 파일 규칙

- 파일명 = 프로젝트 slug (예: `my-saas.yaml` → slug = `my-saas`)
- `_template.yaml`, `README.md` 는 무시됨
- 모든 `.yaml` 파일이 자동 로드됨 (`config.py:load_all_projects()`)

## 필드 명세

### product (필수)

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `name` | string | 제품명 | `"사주마케팅"` |
| `tagline` | string | 한 줄 설명 | `"AI 사주 운세 자동화"` |
| `website` | string | 제품 URL | `"https://saju.app"` |
| `category` | string | **★ 채널 자동 판별 기준** | 아래 표 참조 |

#### category 값 → 채널 매핑

| category | 타입 | 자동 배정 채널 |
|----------|------|---------------|
| `consumer` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `entertainment` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `lifestyle` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `health` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `education` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `fortune` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `astrology` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `gaming` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `social` | B2C | IG Reels, TikTok, YT Shorts, 네이버블로그 |
| `developer-tools` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `saas` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `devops` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `api` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `infrastructure` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `analytics` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `security` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `productivity` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |
| `enterprise` | B2B | Reddit, HN, Product Hunt, Dev.to, 디렉토리 |

category가 위 목록에 없으면 `audience.primary`에서 판별:
- "developer", "engineer", "devops", "technical", "startup" 포함 → B2B
- 그 외 → B2C (기본)

### audience (필수)

| 필드 | 타입 | 설명 |
|------|------|------|
| `primary` | string | 주 타겟 사용자 (category 판별 fallback으로도 사용) |
| `secondary` | string | 보조 타겟 |
| `pain_points` | list[string] | 해결하는 문제들 (콘텐츠 생성 시 참조) |
| `value_props` | list[string] | 핵심 가치 (콘텐츠 생성 시 참조) |

### brand (선택)

| 필드 | 값 | 설명 |
|------|-----|------|
| `tone` | `professional-friendly` / `casual` / `technical` / `playful` | 콘텐츠 톤 |
| `language` | `ko` / `en` | 콘텐츠 언어 |
| `emoji_policy` | `none` / `minimal` / `liberal` | 이모지 사용 수준 |

### seo (권장)

| 필드 | 타입 | 설명 |
|------|------|------|
| `primary_keywords` | list[string] | SEO 주 키워드 (콘텐츠 제목/본문에 삽입) |
| `competitor_domains` | list[string] | 경쟁사 도메인 (competitor-analyst가 분석) |
| `target_monthly_posts` | int | 월 목표 포스트 수 |

### social (선택)

채널별 계정 정보. `enabled: true`로 설정한 채널만 해당 에이전트가 활성화.

```yaml
social:
  twitter:
    handle: "@myhandle"
    enabled: true
  reddit:
    subreddits: ["r/python", "r/machinelearning"]
    enabled: true
```

### schedule (선택)

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `content_days` | 월~금 | 콘텐츠 생성 요일 |
| `social_days` | 월~금 | SNS 게시 요일 |
| `report_day` | friday | 주간 리포트 생성 요일 |
| `timezone` | `Asia/Seoul` | cron 기준 시간대 |

## 예시: B2C (사주)

```yaml
product:
  name: "사주마케팅"
  tagline: "매일 새로운 사주 운세 콘텐츠"
  category: "fortune"           # → B2C → IG, TikTok, YT Shorts, 네이버블로그

audience:
  primary: "20-40대 운세에 관심있는 한국인"
  pain_points:
    - "신뢰할 수 있는 운세 소스 부족"
  value_props:
    - "AI 기반 매일 새로운 사주 운세"

brand:
  tone: "playful"
  language: "ko"

seo:
  primary_keywords: ["오늘의 운세", "사주 운세", "별자리 운세"]
```

## 예시: B2B (개발자 도구)

```yaml
product:
  name: "CodeReviewBot"
  tagline: "AI-powered code review for teams"
  category: "developer-tools"   # → B2B → Reddit, HN, PH, Dev.to, 디렉토리

audience:
  primary: "backend developers"
  pain_points:
    - "Code review takes too long"
  value_props:
    - "50% faster code reviews with AI"

brand:
  tone: "technical"
  language: "en"

seo:
  primary_keywords: ["AI code review", "automated code review"]
  competitor_domains: ["coderabbit.ai", "sourcery.ai"]
```

## 처리 흐름

```
projects/*.yaml
  → config.py:load_all_projects() — 모든 YAML 로드
  → config.py:detect_project_type() — B2C/B2B 판별
  → config.py:get_channels() — 채널 자동 배정
  → zeroclaw SOP — 프로젝트별 순회 실행
  → 각 에이전트가 project YAML 참조하여 콘텐츠 생성
```
