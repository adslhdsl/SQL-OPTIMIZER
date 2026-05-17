# SQL Optimizer Agent

SQL 쿼리와 실행 계획을 입력하면 AI(Gemini 2.5 Flash)가 스스로 DB 구조를 파악하고  
인덱스 추가·쿼리 재작성 등 구체적인 최적화 방안을 한국어로 제안하는 에이전트입니다.

> 에이전트(Agent) 학습 목적으로 제작된 프로젝트입니다.  
> 자세한 동작 원리는 `docs/index.html`을 브라우저로 열어 확인하세요.

---

## 시작하기

### 요구사항

- Python 3.10 이상
- Gemini API 키 ([발급 방법](#api-키-발급))

### 1. 저장소 클론

```bash
git clone https://github.com/adslhdsl/SQL-OPTIMIZER.git
cd sql-optimizer
```

### 2. 가상 환경 생성 및 활성화

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. API 키 발급

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. **Create API key** 클릭
3. 발급된 키 복사

### 5. .env 파일 생성

프로젝트 루트에 `.env` 파일을 직접 만들고 아래 내용을 붙여넣습니다.

```
GEMINI_API_KEY=발급받은_키_여기에_입력
```

### 6. 샘플 DB 생성

```bash
python setup_db.py
```

인덱스가 없는 상태의 테이블 3개가 생성됩니다 (최적화 실습용).

```
customers — 1,000건   (id, name, email, region, created_at)
products  —   200건   (id, name, category, price)
orders    — 10,000건  (id, customer_id, product_id, quantity, status, ordered_at)
```

### 7. 실행

```bash
python agent.py
```

---

## 사용 방법

`agent.py` 하단의 두 변수를 분석하고 싶은 쿼리로 교체하세요.

```python
test_query = """
SELECT c.name, COUNT(o.id) AS order_count
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE c.region = 'Seoul'
GROUP BY c.id
ORDER BY order_count DESC
LIMIT 10;
"""

test_explain = """
QUERY PLAN
|--SCAN orders
|--SEARCH customers USING INTEGER PRIMARY KEY (rowid=?)
`--USE TEMP B-TREE FOR GROUP BY
"""
```

`test_explain`에는 실제 DB에서 `EXPLAIN QUERY PLAN <쿼리>`를 직접 실행한 결과를 붙여넣습니다.

에이전트가 DB 스키마와 인덱스를 자동으로 수집한 뒤 최적화 제안을 출력합니다.

---

## 프로젝트 구조

```
sql-optimizer/
├── agent.py          # 메인 에이전트 (Gemini 호출 + 도구 루프)
├── mcp_server.py     # MCP 서버 (Claude Code 연동용, 선택사항)
├── setup_db.py       # 샘플 DB 생성 스크립트
├── requirements.txt  # 의존성
├── .env              # API 키 (직접 생성, git 제외)
└── docs/
    └── index.html    # 프로젝트 및 에이전트 동작 원리 설명 문서
```

---

## 주의사항

- `.env` 파일은 절대 git에 올리지 마세요. `.gitignore`에 이미 포함되어 있습니다.
- 에이전트는 DB의 실제 데이터를 읽지 않습니다. 스키마·인덱스·행 수만 조회합니다.
- API 호출 횟수 제한(429) 발생 시 자동으로 60초 대기 후 재시도합니다.
