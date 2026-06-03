# 📊 포트폴리오 데일리 브리핑 자동화

매일 아침 **한국시간 오전 7시**에 자동으로 실행됩니다.
- 📲 **카카오톡** — 200자 핵심 요약
- 📧 **Gmail** — 주가 + 뉴스 풀 브리핑 HTML 이메일

---

## 🗂️ 파일 구조

```
portfolio-briefing/
├── .github/
│   └── workflows/
│       └── daily_briefing.yml   # GitHub Actions 스케줄러
├── briefing.py                  # 메인 실행 스크립트
├── requirements.txt
└── README.md
```

---

## 🚀 설정 방법 (5단계)

### 1단계 — GitHub 리포지토리 생성

1. [github.com](https://github.com) 로그인
2. 우상단 **+** → **New repository**
3. Repository name: `portfolio-briefing`
4. **Private** 선택 (API 키 보호)
5. **Create repository** 클릭

---

### 2단계 — 파일 업로드

리포지토리에 아래 파일들을 업로드합니다.

```
briefing.py
requirements.txt
.github/workflows/daily_briefing.yml
```

> **주의:** `.github/workflows/` 폴더 구조 그대로 업로드해야 합니다.

---

### 3단계 — Secrets 등록

리포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 | 얻는 방법 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `PLAYMCP_TOKEN` | PlayMCP Bearer 토큰 | [playmcp.kakao.com](https://playmcp.kakao.com) → 내 토큰 |
| `GMAIL_USER` | `yourname@gmail.com` | 본인 Gmail 주소 |
| `GMAIL_APP_PASSWORD` | 16자리 앱 비밀번호 | 아래 Gmail 앱 비밀번호 발급 참고 |
| `RECIPIENT_EMAIL` | 수신할 이메일 주소 | 브리핑 받을 이메일 |

#### Gmail 앱 비밀번호 발급
1. Google 계정 → **보안** → **2단계 인증** 활성화 (필수)
2. **앱 비밀번호** 검색 → 앱: `메일`, 기기: `Windows 컴퓨터`
3. 생성된 **16자리 비밀번호** 복사 → `GMAIL_APP_PASSWORD`에 입력

---

### 4단계 — 수동 테스트 실행

1. 리포지토리 → **Actions** 탭
2. 좌측 **포트폴리오 데일리 브리핑** 클릭
3. **Run workflow** → **Run workflow** 클릭
4. 카카오톡 & 이메일 수신 확인 ✅

---

### 5단계 — 자동 스케줄 확인

- 매일 **UTC 22:00 = 한국시간 07:00** 자동 실행
- Actions 탭에서 실행 로그 확인 가능
- 실패 시 GitHub가 이메일로 알림 발송

---

## ⚠️ 주의사항

- GitHub Actions 무료 플랜: 월 **2,000분** 제공 (1회 실행 약 1~2분 → 연간 충분)
- `briefing.py` 상단 종목 리스트를 수정하면 다른 종목 추가 가능
- KRX는 장 마감(오후 3시 30분) 이후 데이터가 확정됨 → 오전 7시엔 전일 종가 기준
