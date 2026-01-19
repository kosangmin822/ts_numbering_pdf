# WORKLOG RULE

## Purpose
- Prevent repeated wrong approaches  
  - 동일한 잘못을 반복하지 않기 위함
- Record decisions and rationale  
  - 왜 그 선택을 했는지를 남기기 위함
- Enable multi-agent collaboration  
  - 여러 AI 및 사람이 함께 작업하기 위함

## What this is
- A rulebook for writing WORKLOG entries  
  - WORKLOG 작성 기준 문서
- Not a knowledge base  
  - 지식 정리 문서가 아님
- Not meant to be read every time  
  - 매번 읽으라고 만든 문서가 아님

## When to write
- At the end of a meaningful work session  
  - 의미 있는 작업 단위가 끝났을 때
- When a decision, failure, or architectural change occurred  
  - 결정 / 실패 / 구조 변경이 있었을 때
- When getting stuck and switching approach  
  - 막혀서 접근 방식을 바꿀 때

## Logging flow
- Always write WORKLOG entries using WORKLOG_TEMPLATE.md  
  - 모든 WORKLOG는 TEMPLATE를 기반으로 작성한다
- Append each session to WORKLOG.md (do not overwrite)  
  - 세션 로그는 WORKLOG.md에 **누적 저장**한다

## AI Fast Context update rule
- At the end of each session, update the **AI Fast Context** section in WORKLOG.md  
  - 각 세션 종료 시 Fast Context를 갱신한다
- Fast Context must reflect the **latest confirmed state only**  
  - 최신에 확정된 상태만 반영한다
- Do not include history or speculation in Fast Context  
  - 과거 이력이나 추측은 포함하지 않는다

## Must include (minimum)
- Intent (이번 세션의 목표)
- Changes (무엇을 바꿨는지)
- Result (결과)
- Wrong turns (실패한 접근과 이유)
- Decision (내린 결정과 근거)

## Agent tagging rule
- Agent is labeled by execution environment, not AI self-identity  
  - AI가 주장한 정체성이 아니라 실제 사용 환경 기준
- Allowed agents:
  - Cursor
  - Codex
  - Anti-Gravity
  - Claude
  - Human

## Writing principles
- Be concise and factual  
  - 짧고 사실 위주
- One session = one main intent  
  - 한 세션에 하나의 핵심 목표
- Record failures as reusable knowledge  
  - 실패는 반드시 자산으로 남긴다
- Avoid speculation without evidence  
  - 근거 없는 추측 금지
