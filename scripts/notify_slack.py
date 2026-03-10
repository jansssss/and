"""
퇴직금운용계획.md에서 실행 예정일을 읽어,
내일(KST 기준)이 실행 예정일이면 Slack DM을 발송한다.

필요한 환경변수:
    SLACK_BOT_TOKEN  : Slack Bot OAuth Token (xoxb-...)
    SLACK_USER_ID    : DM을 받을 슬랙 유저 ID (U...)
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
tomorrow_kst: date = (datetime.now(KST) + timedelta(days=1)).date()

MD_PATH = "퇴직금운용계획.md"

# ── 마크다운 읽기 ──────────────────────────────────────────────────────────────
with open(MD_PATH, encoding="utf-8") as f:
    content = f.read()

# ── 실행 예정일 목록 파싱 ────────────────────────────────────────────────────
# 패턴: "2차 실행 예정일: 2026-04-10"
date_pattern = re.compile(r"(\d+)차 실행 예정일:\s*(\d{4}-\d{2}-\d{2})")
matches = date_pattern.findall(content)

target = None
for round_str, date_str in matches:
    exec_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if exec_date == tomorrow_kst:
        target = (int(round_str), date_str)
        break

if not target:
    print(f"내일({tomorrow_kst})은 실행 예정일이 아닙니다. 알림 없음.")
    sys.exit(0)

round_num, date_str = target

# ── 해당 차수의 목표·금액 섹션 추출 ─────────────────────────────────────────
def extract_list_section(header: str) -> str:
    """헤더 다음에 나오는 불릿 리스트를 반환한다."""
    pattern = re.compile(rf"{re.escape(header)}\n((?:- .+\n)+)", re.MULTILINE)
    m = pattern.search(content)
    return m.group(1).rstrip() if m else "(정보 없음)"

goals_text   = extract_list_section(f"{round_num}차 실행 목표:")
amounts_text = extract_list_section(f"{round_num}차 목표 금액:")

# ── Slack 메시지 구성 ────────────────────────────────────────────────────────
message = (
    f"📌 *[퇴직금 운용] {round_num}차 분할 매수 예정일이 내일입니다*\n"
    f"📅 실행 예정일: *{date_str}*\n\n"
    f"*{round_num}차 실행 목표*\n{goals_text}\n\n"
    f"*{round_num}차 목표 금액*\n{amounts_text}\n\n"
    "━━━━━━━━━━━━━━━\n"
    "*매수 전 필수 점검 항목*\n"
    "1. 예금형 4.5% 금리 유지 여부\n"
    "2. 미국 대형주 / 반도체 / KOSPI 최근 흐름\n"
    "3. 지정학 리스크 (전쟁, 유가, 환율)\n"
    "4. 해당 펀드 판매 지속 여부 / 총보수 변경 여부\n\n"
    "이상 없으면 계획대로 진행하세요."
)

# ── Slack DM 발송 ────────────────────────────────────────────────────────────
token   = os.environ["SLACK_BOT_TOKEN"]
user_id = os.environ["SLACK_USER_ID"]

payload = json.dumps(
    {"channel": user_id, "text": message, "unfurl_links": False}
).encode("utf-8")

req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=payload,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    },
)

with urllib.request.urlopen(req, timeout=10) as resp:
    result = json.loads(resp.read())

if result.get("ok"):
    print(f"Slack DM 발송 완료 — {round_num}차 실행 예정일 {date_str}")
else:
    print(f"Slack 발송 실패: {result.get('error')}")
    sys.exit(1)
