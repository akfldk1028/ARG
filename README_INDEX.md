# AG/Agent - 프로젝트 README 인덱스

> 19개의 AI 에이전트 프로젝트 모음 — 전체 A2A Protocol 연동 완료

## 빠른 참조

| 프로젝트 | 난이도 | 프레임워크 | A2A 포트 | 설명 |
|---------|-------|-----------|---------|------|
| [my-first-agent](#my-first-agent) | 입문 | OpenAI SDK | 9017 | 기본 에이전트 학습 |
| [hello-langgraph](#hello-langgraph) | 입문 | LangGraph | 9004 | 시 작성 봇 |
| [chatgpt-clone](#chatgpt-clone) | 중급 | OpenAI Agents | 9001 | ChatGPT 클론 |
| [customer-support-agent](#customer-support-agent) | 중급 | OpenAI Agents | 9002 | 고객 지원 멀티 에이전트 |
| [tutor-agent](#tutor-agent) | 중급 | LangGraph | 9003 | AI 튜터 시스템 |
| [financial-analyst](#financial-analyst) | 고급 | Google ADK | 9012 | 금융 분석 |
| [a2a](#a2a) | 고급 | ADK + LangGraph | 8001, 8002 | 에이전트 간 통신 (네이티브) |
| [law-domain-agents](#law-domain-agents) | 고급 | LangGraph + A2A | 8011 | 법률 검색 멀티 에이전트 (네이티브) |

---

## A2A Protocol 포트 맵

모든 에이전트가 A2A Protocol (JSON-RPC 2.0)을 통해 AutoGen Studio에서 호출 가능합니다.

### 네이티브 A2A (기존)
| 프로젝트 | 포트 | 엔드포인트 | 프레임워크 |
|---------|------|-----------|-----------|
| a2a (History) | 8001 | `http://127.0.0.1:8001/` | Google ADK `to_a2a()` |
| a2a (Philosophy) | 8002 | `http://127.0.0.1:8002/messages` | LangGraph + FastAPI |
| a2a_demo (Poetry) | 8003 | `http://127.0.0.1:8003/` | Google ADK `to_a2a()` |
| a2a_demo (Calculator) | 8006 | `http://127.0.0.1:8006/` | Google ADK `to_a2a()` |
| a2a_demo (GUI Test) | 8120 | `http://127.0.0.1:8120/` | Google ADK `to_a2a()` |
| law-domain-agents | 8011 | `http://127.0.0.1:8011/messages/domain-1` | FastAPI A2A |

### A2A 래퍼 (신규 추가)
| 프로젝트 | 포트 | 실행 | 프레임워크 |
|---------|------|------|-----------|
| chatgpt-clone | 9001 | `python a2a_server.py` | OpenAI Agents |
| customer-support-agent | 9002 | `python a2a_server.py` | OpenAI Agents |
| tutor-agent | 9003 | `python a2a_server.py` | LangGraph |
| hello-langgraph | 9004 | `python a2a_server.py` | LangGraph |
| multi-agent-architectures | 9005 | `python a2a_server.py` | LangGraph |
| content-pipeline-agent | 9006 | `python a2a_server.py` | CrewAI |
| job-hunter-agent | 9007 | `python a2a_server.py` | CrewAI |
| news-reader-agent | 9008 | `python a2a_server.py` | CrewAI |
| youtube-thumbnail-maker | 9009 | `python a2a_server.py` | LangGraph |
| workflow-testing | 9010 | `python a2a_server.py` | LangGraph |
| deployment | 9011 | `python a2a_server.py` | OpenAI Agents |
| financial-analyst | 9012 | `python a2a_server.py` | Google ADK |
| deep-research-clone | 9013 | `python a2a_server.py` | AutoGen |
| email-refiner-agent | 9014 | `python a2a_server.py` | Google ADK |
| youtube-shorts-maker | 9015 | `python a2a_server.py` | Google ADK |
| workflow-architectures | 9016 | `python a2a_server.py` | LangGraph |
| my-first-agent | 9017 | `python a2a_server.py` | OpenAI SDK |
| plan-agent | 9018 | `python a2a_server.py` | Claude Code CLI |

### A2A 서버 실행 방법
```bash
# 각 프로젝트 폴더에서
cd AG/agent/<project-name>
python a2a_server.py

# 전체 실행 (PowerShell)
Get-ChildItem -Path "D:\Data\25_ACE\AG\agent" -Recurse -Filter "a2a_server.py" | ForEach-Object {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $($_.DirectoryName); python a2a_server.py"
}
```

---

## 프레임워크별 분류

### OpenAI Agents
- [my-first-agent](./my-first-agent/) - 기본 에이전트 (A2A: 9017)
- [chatgpt-clone](./chatgpt-clone/) - ChatGPT 클론 (A2A: 9001)
- [customer-support-agent](./customer-support-agent/) - 고객 지원 (A2A: 9002)
- [deployment](./deployment/) - 프로덕션 배포 (A2A: 9011)

### LangGraph
- [hello-langgraph](./hello-langgraph/) - 시 작성 봇 (A2A: 9004)
- [tutor-agent](./tutor-agent/) - AI 튜터 (A2A: 9003)
- [youtube-thumbnail-maker](./youtube-thumbnail-maker/) - 썸네일 생성 (A2A: 9009)
- [workflow-architectures](./workflow-architectures/) - 워크플로우 패턴 (A2A: 9016)
- [workflow-testing](./workflow-testing/) - 에이전트 테스트 (A2A: 9010)
- [multi-agent-architectures](./multi-agent-architectures/) - 멀티 에이전트 패턴 (A2A: 9005)

### Google ADK
- [financial-analyst](./financial-analyst/) - 금융 분석 (A2A: 9012)
- [youtube-shorts-maker](./youtube-shorts-maker/) - YouTube Shorts 제작 (A2A: 9015)
- [email-refiner-agent](./email-refiner-agent/) - 이메일 개선 (A2A: 9014)
- [a2a](./a2a/) - Agent-to-Agent 통신 (네이티브 A2A: 8001, 8002)

### CrewAI (Python 3.11)
- [content-pipeline-agent](./content-pipeline-agent/) - 콘텐츠 파이프라인 (A2A: 9006)
- [job-hunter-agent](./job-hunter-agent/) - 구직 자동화 (A2A: 9007)
- [news-reader-agent](./news-reader-agent/) - 뉴스 수집 (A2A: 9008)

### Claude Code CLI
- [plan-agent](./plan-agent/) - 코드 분석 & 구현 계획 (A2A: 9018)

### AutoGen
- [deep-research-clone](./deep-research-clone/) - 심층 리서치 (A2A: 9013)

### 법률 도메인 (커스텀)
- [law-domain-agents](./law-domain-agents/) - 법률 검색 A2A 에이전트 (네이티브 A2A: 8011)
- [law-domain-setup](./law-domain-setup/) - Neo4j 도메인 초기화

---

## 프로젝트 상세

### my-first-agent
- **난이도**: 입문
- **프레임워크**: OpenAI SDK
- **설명**: 가장 기본적인 AI 에이전트. 에이전트 기초 학습용.
- **A2A 포트**: 9017
- **실행**: `uv run jupyter notebook main.ipynb`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./my-first-agent/README_KO.md)

### hello-langgraph
- **난이도**: 입문
- **프레임워크**: LangGraph
- **설명**: 시를 작성하는 Mr. Poet 에이전트. 사용자 피드백으로 시 개선.
- **포트**: 8101 (LangGraph Dev) / **A2A 포트**: 9004
- **실행**: `uv run langgraph dev`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./hello-langgraph/README_KO.md)

### chatgpt-clone
- **난이도**: 중급
- **프레임워크**: OpenAI Agents + Streamlit
- **설명**: 웹 검색, 이미지 생성, 코드 실행 기능의 ChatGPT 클론.
- **포트**: 8501 (Streamlit) / **A2A 포트**: 9001
- **실행**: `uv run streamlit run main.py`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./chatgpt-clone/README_KO.md)

### customer-support-agent
- **난이도**: 중급
- **프레임워크**: OpenAI Agents + Streamlit
- **설명**: 5개 전문 에이전트로 구성된 고객 지원 시스템. 음성 지원 포함.
- **포트**: 8502 (Streamlit) / **A2A 포트**: 9002
- **실행**: `uv run streamlit run main.py`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./customer-support-agent/README_KO.md)

### tutor-agent
- **난이도**: 중급
- **프레임워크**: LangGraph
- **설명**: AI 튜터 시스템. 학습 지원 에이전트.
- **포트**: 8102 / **A2A 포트**: 9003
- **실행**: `uv run python main.py`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./tutor-agent/README_KO.md)

### financial-analyst
- **난이도**: 고급
- **프레임워크**: Google ADK
- **설명**: 주식 데이터, 뉴스 분석, 투자 조언 제공.
- **API 키**: Google Gemini, Firecrawl
- **A2A 포트**: 9012
- **실행**: `uv run python -m financial_advisor.agent`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./financial-analyst/README_KO.md)

### a2a
- **난이도**: 고급
- **프레임워크**: Google ADK + LangGraph
- **설명**: Agent-to-Agent 통신. HistoryHelper(8001), PhilosophyHelper(8002), StudentHelper.
- **A2A 포트**: 8001, 8002 (네이티브)
- **실행**: 3개 터미널 필요
- **README**: [README_KO.md](./a2a/README_KO.md)

### multi-agent-architectures
- **난이도**: 중급
- **프레임워크**: LangGraph
- **설명**: 멀티 에이전트 패턴 학습 (Swarm, Supervisor, Hierarchical, Network).
- **포트**: 8103 / **A2A 포트**: 9005
- **실행**: `uv run python graph.py`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./multi-agent-architectures/README_KO.md)

### deep-research-clone
- **난이도**: 고급
- **프레임워크**: AutoGen
- **설명**: 심층 리서치 자동화. 복잡한 주제 조사 및 보고서 작성.
- **API 키**: OpenAI, Firecrawl
- **A2A 포트**: 9013
- **실행**: `uv run jupyter notebook`
- **A2A 실행**: `python a2a_server.py`
- **README**: [README_KO.md](./deep-research-clone/README_KO.md)

### law-domain-agents
- **난이도**: 고급
- **프레임워크**: LangGraph + A2A Protocol
- **설명**: 법률 조항 검색 멀티 에이전트 시스템. Neo4j 기반.
- **A2A 포트**: Coordinator(8010), Domain1-5(8011-8015) (네이티브)
- **필요**: Neo4j Database
- **README**: [README.md](./law-domain-agents/README.md)
- **상태**: [STATUS.md](./law-domain-agents/STATUS.md)

### law-domain-setup
- **설명**: law-domain-agents를 위한 Neo4j 초기화 스크립트
- **README**: [README.md](./law-domain-setup/README.md)

### content-pipeline-agent
- **난이도**: 중급
- **프레임워크**: CrewAI
- **설명**: 콘텐츠 파이프라인 자동화.
- **A2A 포트**: 9006
- **A2A 실행**: `python a2a_server.py`

### job-hunter-agent
- **난이도**: 중급
- **프레임워크**: CrewAI
- **설명**: 구직 자동화 에이전트.
- **A2A 포트**: 9007
- **A2A 실행**: `python a2a_server.py`

### news-reader-agent
- **난이도**: 중급
- **프레임워크**: CrewAI
- **설명**: 뉴스 수집 및 분석 에이전트.
- **A2A 포트**: 9008
- **A2A 실행**: `python a2a_server.py`

### youtube-thumbnail-maker
- **난이도**: 중급
- **프레임워크**: LangGraph
- **설명**: YouTube 썸네일 자동 생성.
- **A2A 포트**: 9009
- **A2A 실행**: `python a2a_server.py`

### youtube-shorts-maker
- **난이도**: 중급
- **프레임워크**: Google ADK
- **설명**: YouTube Shorts 자동 제작.
- **A2A 포트**: 9015
- **A2A 실행**: `python a2a_server.py`

### email-refiner-agent
- **난이도**: 중급
- **프레임워크**: Google ADK
- **설명**: 이메일 문구 개선 에이전트.
- **A2A 포트**: 9014
- **A2A 실행**: `python a2a_server.py`

### workflow-architectures
- **난이도**: 중급
- **프레임워크**: LangGraph
- **설명**: 다양한 워크플로우 아키텍처 패턴 학습.
- **A2A 포트**: 9016
- **A2A 실행**: `python a2a_server.py`

### workflow-testing
- **난이도**: 중급
- **프레임워크**: LangGraph
- **설명**: 에이전트 테스트 방법론.
- **A2A 포트**: 9010
- **A2A 실행**: `python a2a_server.py`

### deployment
- **난이도**: 중급
- **프레임워크**: OpenAI Agents
- **설명**: 프로덕션 배포 패턴.
- **A2A 포트**: 9011
- **A2A 실행**: `python a2a_server.py`

### plan-agent
- **난이도**: 중급
- **프레임워크**: Claude Code CLI
- **설명**: Claude Code CLI의 `--permission-mode plan`을 사용하여 코드베이스를 분석하고 구현 계획을 생성하는 에이전트. 파일을 수정하지 않는 읽기 전용 모드.
- **A2A 포트**: 9018
- **실행**: `python a2a_server.py`
- **필요**: Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- **환경변수**: `PLAN_AGENT_WORK_DIR` (기본값: `D:/Data/25_ACE`)

---

## 추가 리소스

### 가이드 문서
- [README_KO.md](./README_KO.md) - 전체 프로젝트 가이드 (한국어)
- [LANGGRAPH_USAGE_GUIDE.md](./LANGGRAPH_USAGE_GUIDE.md) - LangGraph 사용법
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - 설정 가이드

### 쿡북 (Cookbook)
- [a2a_mcp](./cookbook/a2a_mcp/) - A2A + MCP 연동
- [google-adk](./cookbook/google-adk/) - Google ADK 레시피
- [langchain](./cookbook/langchain/) - LangChain 레시피
- [prompting](./cookbook/prompting/) - 프롬프팅 기법

---

## 학습 순서 권장

### Phase 1: 기초 (1-2주)
1. `my-first-agent` - OpenAI 기본
2. `hello-langgraph` - LangGraph 기본
3. `chatgpt-clone` - 실용적인 UI

### Phase 2: 패턴 학습 (2-3주)
4. `workflow-architectures` - 다양한 패턴
5. `multi-agent-architectures` - 멀티 에이전트
6. `workflow-testing` - 테스트 방법

### Phase 3: 실전 프로젝트 (3-4주)
7. `customer-support-agent` - 고객 지원
8. `tutor-agent` - 교육 시스템
9. `content-pipeline-agent` - 콘텐츠 자동화

### Phase 4: 고급 (4주+)
10. `financial-analyst` - 금융 분석
11. `deep-research-clone` - 심층 리서치
12. `a2a` - 에이전트 간 통신
13. `law-domain-agents` - 법률 도메인 전문가 시스템

---

## 필요한 API 키

| API | 프로젝트 | 발급처 |
|-----|---------|-------|
| OpenAI | 대부분 (17개) | https://platform.openai.com/api-keys |
| Google Gemini | financial-analyst, a2a 등 | https://makersuite.google.com/app/apikey |
| Firecrawl | deep-research-clone, content-pipeline-agent | https://firecrawl.dev |

---

## 환경 설정

### Python 버전
- **3.13**: 대부분의 프로젝트 (14개)
- **3.11**: CrewAI 프로젝트 (3개) - ChromaDB 호환성

### 패키지 관리
- **uv**: 모든 프로젝트에서 사용
- 각 프로젝트별 독립 가상환경 (.venv)

---

## AutoGen Studio 연동

모든 에이전트는 AutoGen Studio Gallery 11 (v3.0.0)에 A2A Protocol Team으로 등록되어 있습니다.
Playground에서 "Auto-Claude A2A Protocol Team" 선택 후 자연어로 에이전트를 호출할 수 있습니다.

```
AutoGen Studio → Playground → A2A Protocol Team → "역사에 대해 질문" → History Agent (8001) 자동 호출
```

---

**마지막 업데이트**: 2026-01-30
