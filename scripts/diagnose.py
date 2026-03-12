"""
퇴직금 운용 자동 진단 스크립트
매일 09:00 KST GitHub Actions로 실행 → diagnosis_result.json 생성
"""
import json
import sys
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def main():
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed")
        sys.exit(1)

    now = datetime.now(KST)

    print("시장 데이터 수집 중...")
    data = yf.download(
        ["^SOX", "^KS11", "CL=F", "KRW=X"],
        period="2mo",
        progress=False,
        auto_adjust=True,
    )
    closes = data["Close"]

    def val(ticker):
        s = closes[ticker].dropna()
        return s.iloc[-1] if len(s) else None

    def pct(ticker, days):
        s = closes[ticker].dropna()
        if len(s) < days:
            return None
        return (s.iloc[-1] - s.iloc[-days]) / s.iloc[-days] * 100

    sox_now  = val("^SOX")
    sox_1m   = pct("^SOX", 22)
    sox_1w   = pct("^SOX", 5)
    kos_now  = val("^KS11")
    kos_1m   = pct("^KS11", 22)
    kos_1w   = pct("^KS11", 5)
    oil_now  = val("CL=F")
    oil_1m   = pct("CL=F", 22)
    krw_now  = val("KRW=X")

    def fmt_pct(v):
        return f"{v:+.1f}%" if v is not None else "N/A"

    items = []

    # ── 1. 예금형 4.9% 고정 계약 ───────────────────────────────────
    items.append({
        "id": "deposit_rate",
        "label": "예금형 4.9% 고정 계약 조건 변경 여부",
        "status": "pass",
        "detail": "고정 계약 — 시장 금리 무관. 조건 변경 없음."
    })

    # ── 2. 시장 흐름 (SOX + KOSPI) ────────────────────────────────
    mkt_status = "pass"
    mkt_warn   = []

    if kos_1m is not None:
        if kos_1m < -10:
            mkt_status = "fail";  mkt_warn.append(f"KOSPI 1개월 {kos_1m:.1f}% 급락")
        elif kos_1m < -5:
            mkt_status = "warning"; mkt_warn.append(f"KOSPI 1개월 {kos_1m:.1f}% 하락")

    if sox_1m is not None:
        if sox_1m < -15:
            mkt_status = "fail";  mkt_warn.append(f"SOX 1개월 {sox_1m:.1f}% 급락")
        elif sox_1m < -8 and mkt_status == "pass":
            mkt_status = "warning"; mkt_warn.append(f"SOX 1개월 {sox_1m:.1f}% 하락")

    mkt_detail = (
        f"SOX: {sox_now:,.0f} (1개월 {fmt_pct(sox_1m)}, 1주 {fmt_pct(sox_1w)}) · "
        f"KOSPI: {kos_now:,.0f} (1개월 {fmt_pct(kos_1m)}, 1주 {fmt_pct(kos_1w)})"
    )
    if mkt_warn:
        mkt_detail += " · ⚠️ " + " / ".join(mkt_warn)

    items.append({
        "id": "market_trend",
        "label": "미국 대형주 / 반도체 / KOSPI 최근 흐름",
        "status": mkt_status,
        "detail": mkt_detail
    })

    # ── 3. 지정학 (유가 + 환율) ──────────────────────────────────
    geo_status = "pass"
    geo_warn   = []

    if oil_1m is not None:
        if oil_1m > 30:
            geo_status = "fail";    geo_warn.append(f"유가 1개월 {oil_1m:+.0f}% 급등 — 시스템 리스크")
        elif oil_1m > 15:
            if geo_status == "pass": geo_status = "warning"
            geo_warn.append(f"유가 1개월 {oil_1m:+.0f}% 상승")

    if krw_now is not None:
        if krw_now > 1500:
            geo_status = "fail";    geo_warn.append(f"USD/KRW {krw_now:.0f}원 — 위험 수준")
        elif krw_now > 1450:
            if geo_status == "pass": geo_status = "warning"
            geo_warn.append(f"USD/KRW {krw_now:.0f}원 — 주의")

    geo_detail = (
        f"WTI: ${oil_now:.0f}/배럴 (1개월 {fmt_pct(oil_1m)}) · "
        f"USD/KRW: {krw_now:.0f}원"
    ) if oil_now and krw_now else "데이터 수집 실패"
    if geo_warn:
        geo_detail += " · ⚠️ " + " / ".join(geo_warn)

    items.append({
        "id": "geopolitical",
        "label": "지정학 리스크 (전쟁, 유가, 환율)",
        "status": geo_status,
        "detail": geo_detail
    })

    # ── 4. 펀드 판매 상태 (수동 확인 대리) ───────────────────────
    items.append({
        "id": "fund_status",
        "label": "해당 펀드 판매 지속 여부 / 총보수 변경",
        "status": "pass",
        "detail": "미래에셋 MSCI AC World · 유리 필라델피아반도체 · 삼성 KOSPI200 — 정상 판매 중 (수동 재확인 권장)"
    })

    # ── 종합 판정 ─────────────────────────────────────────────────
    fail_n = sum(1 for i in items if i["status"] == "fail")
    warn_n = sum(1 for i in items if i["status"] == "warning")

    if fail_n >= 1:
        overall        = "HOLD"
        recommendation = "2차 실행 보류 권고"
        causes = []
        if oil_1m  and oil_1m  > 30:  causes.append(f"유가 1개월 {oil_1m:+.0f}%")
        if krw_now and krw_now > 1480: causes.append(f"USD/KRW {krw_now:.0f}원")
        if kos_1m  and kos_1m  < -10: causes.append(f"KOSPI 1개월 {kos_1m:.1f}%")
        if sox_1m  and sox_1m  < -15: causes.append(f"SOX 1개월 {sox_1m:.1f}%")
        reason = ("리스크 감지: " + " / ".join(causes) if causes else "복합 리스크 감지") + \
                 ". 4월 10일 1주 전 재진단 권고."
        action_items = []
        if oil_1m and oil_1m > 30:
            action_items.append({
                "type": "defer",
                "title": "KOSPI200 배분 이번 차수 제외",
                "detail": f"유가 {oil_1m:+.0f}% 급등 시 국내 인플레이션·금리 상승 압박으로 KOSPI 추가 하락 가능. 2차 계획의 KOSPI200 1% 배분을 3차 이후로 이연."
            })
            action_items.append({
                "type": "modify",
                "title": "MSCI AC World 부분 실행 검토 가능",
                "detail": "MSCI는 USD 자산이라 고환율 환경에서 KRW 기준 수익 보호 효과 있음. 원래 7% 대신 3~5%만 부분 실행 후 유가 안정 대기도 유효한 전략."
            })
        if krw_now and krw_now > 1450:
            action_items.append({
                "type": "monitor",
                "title": "재진단 트리거 조건",
                "detail": "① 유가 WTI $85/배럴 이하 회복 + ② USD/KRW 1,420원 이하 안정 → 두 조건 충족 시 재진단 후 원래 계획 실행."
            })
        if kos_1m and kos_1m < -10:
            action_items.append({
                "type": "modify",
                "title": "KOSPI200 급락 시 역발상 검토",
                "detail": f"KOSPI 1개월 {kos_1m:.1f}%는 장기 저가 매수 기회일 수 있음. 단, 유가·환율 리스크 해소 후 진입이 원칙."
            })
        action_items.append({
            "type": "confirm",
            "title": "4월 3일 재진단 예약 (실행 1주 전)",
            "detail": "4월 10일 2차 실행일 1주 전 동일 진단 재실행. 리스크 해소 시 원래 계획대로, 지속 시 추가 보류 또는 수정안 적용."
        })
    elif warn_n >= 2:
        overall        = "CAUTION"
        recommendation = "신중 검토 후 진행"
        reason = "주의 항목 복수 감지. 매수 금액 축소 또는 MSCI 코어 우선 검토."
        action_items = [
            {
                "type": "modify",
                "title": "매수 금액 50% 축소 실행",
                "detail": "원래 10% 대신 5%만 먼저 집행. MSCI AC World 코어를 우선 채우고 테마(반도체, KOSPI200)는 다음 차수로."
            },
            {
                "type": "monitor",
                "title": "2주 후 잔여분 결정",
                "detail": "시장 흐름 재확인 후 안정되면 잔여 5% 추가 집행."
            }
        ]
    else:
        overall        = "PROCEED"
        recommendation = "2차 실행 계획대로 진행"
        reason = "전 항목 이상 없음. 계획대로 진행."
        action_items = [
            {
                "type": "confirm",
                "title": "2차 계획 그대로 실행",
                "detail": "MSCI AC World 7% + 필라델피아반도체 2% + KOSPI200 1% — 예정금액 3,378,721원."
            },
            {
                "type": "confirm",
                "title": "매수 전 최종 확인",
                "detail": "과학기술공제 앱에서 펀드별 매수 화면 진입 후 금액 입력."
            }
        ]

    result = {
        "generated_at": now.isoformat(),
        "overall": overall,
        "items": items,
        "recommendation": recommendation,
        "reason": reason,
        "action_items": action_items
    }

    with open("diagnosis_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"진단 완료 [{now.strftime('%Y-%m-%d %H:%M KST')}]: {overall} — {recommendation}")


if __name__ == "__main__":
    main()
