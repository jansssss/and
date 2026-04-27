"""
퇴직금 운용 자동 진단 스크립트
Naver Finance 데이터를 기준으로 diagnosis_result.json 생성
"""
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape


KST = timezone(timedelta(hours=9))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_text(url: str, encoding: str = "euc-kr") -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as res:
        body = res.read()
    return body.decode(encoding, errors="replace")


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as res:
        body = res.read()
    return json.loads(body.decode("utf-8"))


def to_float(value: str | float | int | None):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = unescape(value)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = cleaned.replace(",", "").replace("%", "").strip()
    return float(cleaned) if cleaned else None


def pct_from_series(series: list[dict], days: int):
    if len(series) < days:
        return None
    latest = series[0]["close"]
    past = series[days - 1]["close"]
    return (latest - past) / past * 100


def get_kospi_series(pages: int = 5):
    rows = []
    pattern = re.compile(
        r'<td class="date">\s*(\d{4}\.\d{2}\.\d{2})\s*</td>\s*'
        r'<td class="number_1">\s*([\d,.]+)\s*</td>',
        re.S,
    )
    for page in range(1, pages + 1):
        html = fetch_text(
            f"https://finance.naver.com/sise/sise_index_day.naver?code=KOSPI&page={page}"
        )
        for date, close in pattern.findall(html):
            rows.append({"date": date.replace(".", "-"), "close": to_float(close)})
    return rows


def get_sox_series(pages: int = 3):
    rows = []
    for page in range(1, pages + 1):
        data = fetch_json(
            "https://finance.naver.com/world/worldDayListJson.naver"
            f"?symbol=NAS@SOX&fdtc=0&page={page}"
        )
        for item in data:
            ymd = item["xymd"]
            rows.append({
                "date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}",
                "close": to_float(item["clos"]),
            })
    return rows


def get_marketindex_series(marketindex_cd: str, pages: int = 4, fdtc: int | None = None):
    rows = []
    if marketindex_cd.startswith("FX_"):
        url_base = (
            "https://finance.naver.com/marketindex/exchangeDailyQuote.naver"
            f"?marketindexCd={marketindex_cd}"
        )
    else:
        url_base = (
            "https://finance.naver.com/marketindex/worldDailyQuote.naver"
            f"?marketindexCd={marketindex_cd}&fdtc={fdtc or 2}"
        )

    pattern = re.compile(
        r'<td class="date">\s*(\d{4}\.\d{2}\.\d{2})\s*</td>\s*'
        r'<td class="num">\s*([\d,.]+)\s*</td>',
        re.S,
    )
    for page in range(1, pages + 1):
        html = fetch_text(f"{url_base}&page={page}")
        for date, close in pattern.findall(html):
            rows.append({"date": date.replace(".", "-"), "close": to_float(close)})
    return rows


def fmt_pct(v):
    return f"{v:+.1f}%" if v is not None else "N/A"


def fmt_num(v, digits=0, suffix=""):
    if v is None:
        return "N/A"
    return f"{v:,.{digits}f}{suffix}"


def main():
    now = datetime.now(KST)

    print("Naver Finance 시장 데이터 수집 중...")
    kospi = get_kospi_series()
    sox = get_sox_series()
    usdkrw = get_marketindex_series("FX_USDKRW")
    oil = get_marketindex_series("OIL_DU", fdtc=2)

    kos_now = kospi[0]["close"] if kospi else None
    kos_1m = pct_from_series(kospi, 22)
    kos_1w = pct_from_series(kospi, 5)

    sox_now = sox[0]["close"] if sox else None
    sox_1m = pct_from_series(sox, 22)
    sox_1w = pct_from_series(sox, 5)

    krw_now = usdkrw[0]["close"] if usdkrw else None
    oil_now = oil[0]["close"] if oil else None
    oil_1m = pct_from_series(oil, 22)

    items = []

    items.append({
        "id": "deposit_rate",
        "label": "예금형 4.9% 고정 계약 조건 변경 여부",
        "status": "pass",
        "detail": "고정 계약 - 시장 금리 무관. 조건 변경 없음. 별도 약관 변경 공지가 없으면 코어 70% 유지.",
    })

    market_status = "pass"
    market_warn = []
    if kos_1m is not None:
        if kos_1m < -10:
            market_status = "fail"
            market_warn.append(f"KOSPI 1개월 {kos_1m:.1f}% 급락")
        elif kos_1m < -5:
            market_status = "warning"
            market_warn.append(f"KOSPI 1개월 {kos_1m:.1f}% 하락")
        elif kos_1m > 15:
            market_status = "warning"
            market_warn.append(f"KOSPI 1개월 {kos_1m:.1f}% 급등")

    if sox_1m is not None:
        if sox_1m < -15:
            market_status = "fail"
            market_warn.append(f"SOX 1개월 {sox_1m:.1f}% 급락")
        elif sox_1m < -8 and market_status == "pass":
            market_status = "warning"
            market_warn.append(f"SOX 1개월 {sox_1m:.1f}% 하락")
        elif sox_1m > 25 and market_status == "pass":
            market_status = "warning"
            market_warn.append(f"SOX 1개월 {sox_1m:.1f}% 급등")

    market_detail = (
        f"출처: Naver Finance · SOX: {fmt_num(sox_now)} "
        f"(1개월 {fmt_pct(sox_1m)}, 1주 {fmt_pct(sox_1w)}) · "
        f"KOSPI: {fmt_num(kos_now)} (1개월 {fmt_pct(kos_1m)}, 1주 {fmt_pct(kos_1w)})"
    )
    if market_warn:
        market_detail += " · 주의: " + " / ".join(market_warn)

    items.append({
        "id": "market_trend",
        "label": "미국 반도체 / KOSPI 최근 흐름",
        "status": market_status,
        "detail": market_detail,
    })

    geo_status = "pass"
    geo_warn = []
    if oil_1m is not None:
        if oil_1m > 30:
            geo_status = "fail"
            geo_warn.append(f"두바이유 1개월 {oil_1m:+.0f}% 급등")
        elif oil_1m > 15:
            geo_status = "warning"
            geo_warn.append(f"두바이유 1개월 {oil_1m:+.0f}% 상승")
    if krw_now is not None:
        if krw_now > 1500:
            geo_status = "fail"
            geo_warn.append(f"USD/KRW {krw_now:.0f}원 - 위험 수준")
        elif krw_now > 1450:
            if geo_status == "pass":
                geo_status = "warning"
            geo_warn.append(f"USD/KRW {krw_now:.0f}원 - 주의")

    geo_detail = (
        f"출처: Naver Finance · 두바이유: ${fmt_num(oil_now, 2)}/배럴 "
        f"(1개월 {fmt_pct(oil_1m)}) · USD/KRW: {fmt_num(krw_now, 0, '원')}"
    )
    if geo_warn:
        geo_detail += " · 주의: " + " / ".join(geo_warn)

    items.append({
        "id": "geopolitical",
        "label": "지정학 리스크 대리 지표 (유가, 환율)",
        "status": geo_status,
        "detail": geo_detail,
    })

    items.append({
        "id": "fund_status",
        "label": "해당 펀드 판매 지속 여부 / 총보수 변경",
        "status": "pass",
        "detail": "미래에셋 MSCI AC World · 유리 필라델피아반도체 · 삼성 KOSPI200 - 매수 화면에서 판매 여부와 총보수 최종 확인 필요.",
    })

    fail_n = sum(1 for item in items if item["status"] == "fail")
    warn_n = sum(1 for item in items if item["status"] == "warning")

    if fail_n >= 1:
        overall = "HOLD"
        recommendation = "추가 실행 보류 권고"
        reason = "위험 항목 감지. 2차 미집행분이 있다면 오늘 집행하지 말고 유가·환율 안정 후 재진단."
        action_items = [
            {
                "type": "defer",
                "title": "2차 미집행분 보류",
                "detail": "원래 4월 10일 2차 계획은 기한 경과 상태다. 오늘 기준 위험 항목이 해소될 때까지 신규 매수 보류.",
            },
            {
                "type": "monitor",
                "title": "재진단 조건",
                "detail": "USD/KRW 1,450원 이하, 유가 1개월 급등 완화, KOSPI/SOX 급락 없음 조건을 다시 확인.",
            },
        ]
    elif warn_n >= 1:
        overall = "CAUTION"
        recommendation = "신중 검토 후 축소 진행"
        reason = "주의 항목 감지. 2차 실행 예정일은 이미 지났으므로, 미집행 상태라면 금액 축소 또는 MSCI 코어 우선이 적절."
        action_items = [
            {
                "type": "modify",
                "title": "2차 미집행분은 50% 축소",
                "detail": "원래 10% 대신 5% 이내로 먼저 집행. MSCI AC World를 우선하고 반도체·KOSPI200 추가 비중은 다음 재진단까지 보류.",
            },
            {
                "type": "monitor",
                "title": "3차 전 재진단",
                "detail": "2026-05-10 전 다시 Naver Finance 기준으로 유가·환율·KOSPI·SOX를 확인.",
            },
        ]
    else:
        overall = "PROCEED"
        recommendation = "2차 미집행분 진행 가능"
        reason = "오늘 기준 주요 시장·유가·환율 항목에 경고 없음. 2차가 아직 미집행이면 계획대로 진행 가능."
        action_items = [
            {
                "type": "confirm",
                "title": "2차 계획 실행",
                "detail": "MSCI AC World 7% + 필라델피아반도체 2% + KOSPI200 1% - 예정금액 3,378,721원.",
            },
            {
                "type": "confirm",
                "title": "매수 전 최종 확인",
                "detail": "과학기술공제 앱에서 펀드별 판매 상태와 보수를 확인한 뒤 금액 입력.",
            },
        ]

    result = {
        "generated_at": now.isoformat(),
        "data_source": "https://finance.naver.com",
        "overall": overall,
        "items": items,
        "recommendation": recommendation,
        "reason": reason,
        "action_items": action_items,
    }

    with open("diagnosis_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"진단 완료 [{now.strftime('%Y-%m-%d %H:%M KST')}]: {overall} - {recommendation}")


if __name__ == "__main__":
    main()
