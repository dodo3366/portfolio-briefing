"""
포트폴리오 데일리 브리핑 자동화 스크립트
"""

import os
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from pykrx import stock
import yfinance as yf


# ── 환경변수 ──────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL    = os.environ["RECIPIENT_EMAIL"]


# ── 1. 주가 수집 ──────────────────────────────────────────
def fetch_prices() -> dict:
    today = datetime.date.today().strftime("%Y%m%d")
    start = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y%m%d")
    prices = {}

    kr_stocks = {"삼성전자": "005930", "현대자동차": "005380"}
    for name, ticker in kr_stocks.items():
        try:
            df = stock.get_market_ohlcv_by_date(start, today, ticker)
            if not df.empty:
                row  = df.iloc[-1]
                prev = df.iloc[-2]["종가"] if len(df) >= 2 else row["종가"]
                chg  = (row["종가"] - prev) / prev * 100
                prices[name] = {
                    "ticker": ticker, "market": "KRX",
                    "price": int(row["종가"]), "currency": "원",
                    "open": int(row["시가"]), "high": int(row["고가"]),
                    "low": int(row["저가"]), "volume": int(row["거래량"]),
                    "change_pct": round(chg, 2),
                    "date": df.index[-1].strftime("%Y-%m-%d"),
                }
        except Exception as e:
            prices[name] = {"error": str(e)}

    us_stocks = {"엔비디아": "NVDA", "테슬라": "TSLA"}
    for name, ticker in us_stocks.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if not hist.empty:
                row  = hist.iloc[-1]
                prev = hist.iloc[-2]["Close"] if len(hist) >= 2 else row["Close"]
                chg  = (row["Close"] - prev) / prev * 100
                prices[name] = {
                    "ticker": ticker, "market": "NASDAQ",
                    "price": round(row["Close"], 2), "currency": "USD",
                    "open": round(row["Open"], 2), "high": round(row["High"], 2),
                    "low": round(row["Low"], 2), "volume": int(row["Volume"]),
                    "change_pct": round(chg, 2),
                    "date": hist.index[-1].strftime("%Y-%m-%d"),
                }
        except Exception as e:
            prices[name] = {"error": str(e)}

    return prices


# ── 2. 브리핑 HTML 생성 ───────────────────────────────────
def fetch_briefing(prices: dict) -> dict:
    price_summary = "\n".join(
        f"- {name}: {info.get('price','N/A')}{info.get('currency','')} "
        f"({'+' if info.get('change_pct',0)>=0 else ''}{info.get('change_pct','?')}%) "
        f"[{info.get('date','')}]"
        for name, info in prices.items()
    )
    today_str = datetime.date.today().strftime("%Y년 %m월 %d일")

    prompt = f"""오늘은 {today_str}입니다.

[수집된 주가 데이터]
{price_summary}

위 주가 데이터를 바탕으로 포트폴리오 데일리 브리핑 이메일을 작성해주세요.
반드시 아래 JSON 형식만 반환하세요 (코드블록 없이 순수 JSON만):

{{
  "email_subject": "[포트폴리오 브리핑] {today_str}",
  "email_html": "인라인 CSS 포함 완성 HTML. 4개 종목 종가 테이블 + 종목별 분석 코멘트 포함. 상승 초록 하락 빨강. 한국어."
}}"""

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    print(f"🔑 API Key 앞 10자리: {ANTHROPIC_API_KEY[:10]}...")
    print(f"📦 요청 payload 확인: model={payload['model']}, max_tokens={payload['max_tokens']}")

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=120,
    )

    # 오류 시 응답 본문 출력
    if response.status_code != 200:
        print(f"❌ API 오류 상태코드: {response.status_code}")
        print(f"❌ API 오류 응답: {response.text}")
        response.raise_for_status()

    data = response.json()
    full_text = "".join(
        block["text"] for block in data["content"] if block["type"] == "text"
    ).strip()

    # 코드블록 제거
    if "```" in full_text:
        for part in full_text.split("```"):
            part = part.strip().lstrip("json").strip()
            if part.startswith("{"):
                full_text = part
                break

    return json.loads(full_text)


# ── 3. Gmail 발송 ─────────────────────────────────────────
def send_email(subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
    print("✅ Gmail 전송 완료")


# ── 메인 ─────────────────────────────────────────────────
def main():
    print("📊 주가 수집 중...")
    prices = fetch_prices()
    print("prices:", json.dumps(prices, ensure_ascii=False, indent=2))

    print("🤖 브리핑 HTML 생성 중...")
    briefing = fetch_briefing(prices)

    print("📧 Gmail 전송 중...")
    send_email(briefing["email_subject"], briefing["email_html"])

    print("🎉 전송 완료!")


if __name__ == "__main__":
    main()
