# 과학기술공제회 퇴직연금 펀드 분석 대시보드

은퇴 퇴직자금 운용 시각화 | 포트폴리오 운용 시스템

🔗 **라이브 데모**: https://jansssss.github.io/and

---

## 주요 기능

| 탭 | 내용 |
|---|---|
| 💰 수익률 시뮬레이션 | 4가지 포트폴리오별 15년 자산 성장 시뮬레이션 |
| 📊 포트폴리오 추천 | 자산배분 차트 + 추천 펀드 목록 |
| 🔍 펀드 탐색기 | 275개 퇴직연금 펀드 필터/정렬/검색 |
| 🎯 전략 가이드 | 글라이드패스, 비용효과, 시장 대처법 |

## 나의 현황

- 현재 적립금: *xx,xxx만원**
- 연간 불입: **x00만원** (회사 x00 + 본인 x00)
- 정년까지: **15년**
- 현재 전략: 예금 100% @ 4.5%

## 추천 포트폴리오 (균형형)

| 자산 | 비중 | 목표 수익률 |
|---|---|---|
| K200 인덱스 | 25% | |
| 글로벌주식 (MSCI) | 35% | |
| TDF 2040 | 25% | **11.5%/년** |
| 채권/보수형 | 15% | |

> 예금 100% 유지시 15년 후 약 2.2억 → 균형형 전환시 약 4.8억 (+2.6억)

## 로컬 실행 (Dash 서버)

```bash
pip install -r requirements.txt
python app.py
# http://localhost:8050 접속
```

## 데이터

- `펀드+필터+검색-20260310.xlsx` : 2026.03.10 기준 퇴직연금 펀드 데이터
- `fund_data.json` : GitHub Pages용 정적 데이터

## Slack 실행 예정일 알림

`퇴직금운용계획.md`의 실행 예정일 **하루 전** 09:00 KST에 Slack DM을 자동 발송한다.

### GitHub Secrets 설정 (Settings → Secrets → Actions)

| Secret 이름 | 설명 |
|---|---|
| `SLACK_BOT_TOKEN` | Slack Bot OAuth Token (`xoxb-...`) |
| `SLACK_USER_ID` | DM 수신자 슬랙 유저 ID (`U...`) |

### Slack 앱 설정 방법

1. https://api.slack.com/apps → **Create New App** → From scratch
2. **OAuth & Permissions** → Scopes → Bot Token Scopes에 `chat:write` 추가
3. **Install to Workspace** → Bot User OAuth Token 복사 → `SLACK_BOT_TOKEN`에 저장
4. 슬랙에서 본인 프로필 → `...` → **Copy member ID** → `SLACK_USER_ID`에 저장
5. 앱을 본인에게 DM으로 초대 (DM 채널에서 앱 이름 멘션 또는 Add Apps)

> 채널 메시지로 대신하려면: `SLACK_USER_ID` 대신 채널 ID(`C...`)를 사용하면 된다.

### 수동 테스트 방법

1. GitHub → Actions → **Slack Reminder - 퇴직금 실행 예정일** → **Run workflow**
2. 로그에 "알림 없음" 또는 "Slack DM 발송 완료" 표시 확인
3. 테스트 시 내일 날짜와 `퇴직금운용계획.md`의 예정일이 일치해야 DM이 발송됨
   - 임시 테스트: `퇴직금운용계획.md`의 예정일 중 하나를 내일 날짜로 바꾼 뒤 수동 실행

### 스케줄 시간 변경

`.github/workflows/notify.yml`의 cron 값을 수정한다:
```
'0 0 * * *'   → 09:00 KST (현재 설정)
'0 23 * * *'  → 08:00 KST
'30 0 * * *'  → 09:30 KST
```

---
*본 분석은 참고용이며 실제 투자 결정 전 전문가 상담을 권장합니다.*
