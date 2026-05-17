import sqlite3
import json
import os
import sys
import time
from google import genai
from google.genai import types, errors
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

DB_PATH = "sample.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_tables() -> str:
    """DB의 모든 테이블 목록을 반환합니다."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    return json.dumps([r["name"] for r in rows])


def get_schema(table_name: str) -> str:
    """특정 테이블의 컬럼 구조를 반환합니다."""
    conn = get_conn()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    conn.close()
    if not rows:
        return f"테이블 '{table_name}' 을 찾을 수 없습니다."
    schema = [
        {"column": r["name"], "type": r["type"], "not_null": bool(r["notnull"]), "pk": bool(r["pk"])}
        for r in rows
    ]
    return json.dumps(schema, ensure_ascii=False)


def get_indexes(table_name: str) -> str:
    """특정 테이블의 인덱스 목록을 반환합니다."""
    conn = get_conn()
    indexes = conn.execute(f"PRAGMA index_list({table_name})").fetchall()
    result = []
    for idx in indexes:
        cols = conn.execute(f"PRAGMA index_info({idx['name']})").fetchall()
        result.append({
            "index_name": idx["name"],
            "unique": bool(idx["unique"]),
            "columns": [c["name"] for c in cols],
        })
    conn.close()
    if not result:
        return f"'{table_name}' 테이블에 인덱스가 없습니다."
    return json.dumps(result, ensure_ascii=False)


def get_table_stats(table_name: str) -> str:
    """테이블의 행 수와 기본 통계를 반환합니다."""
    conn = get_conn()
    try:
        count = conn.execute(
            f"SELECT COUNT(*) as cnt FROM {table_name}"
        ).fetchone()["cnt"]
        conn.close()
        return json.dumps({"table": table_name, "row_count": count})
    except Exception as e:
        conn.close()
        return f"오류: {str(e)}"


TOOL_FUNCTIONS = [get_all_tables, get_schema, get_indexes, get_table_stats]
TOOL_MAP = {fn.__name__: fn for fn in TOOL_FUNCTIONS}

SYSTEM_PROMPT = """당신은 SQL 최적화 전문가입니다.
사용자가 제공한 SQL 쿼리와 실행 계획(EXPLAIN QUERY PLAN 결과)을 분석하고,
제공된 도구를 사용해서 DB 스키마, 인덱스, 테이블 통계를 파악한 뒤,
구체적인 최적화 방법을 한국어로 제안해주세요.

실행 계획은 사용자가 직접 운영 DB에서 실행한 결과이므로 이를 신뢰하고 분석하세요.

최적화 제안에는 다음을 포함해주세요:
1. 현재 쿼리의 문제점 (실행 계획 기반)
2. 인덱스 추가/수정 제안 (CREATE INDEX 구문 포함)
3. 쿼리 재작성 제안 (있는 경우)
4. 예상 성능 개선 효과"""


def run_agent(sql_query: str, explain_result: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수를 설정해주세요. (.env 파일 또는 시스템 환경변수)")

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOL_FUNCTIONS,
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=(
                f"다음 SQL 쿼리를 최적화해주세요.\n\n"
                f"[SQL 쿼리]\n{sql_query}\n\n"
                f"[EXPLAIN QUERY PLAN 결과 (운영 DB에서 직접 실행)]\n{explain_result}"
            ))]
        )
    ]

    for _ in range(10):
        for attempt in range(5):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config,
                )
                break
            except errors.ClientError as e:
                if e.code == 429 and attempt < 4:
                    print(f"  [속도 제한] 60초 대기 후 재시도...")
                    time.sleep(60)
                else:
                    raise

        candidate = response.candidates[0]
        if candidate.content is None:
            return response.text or "응답을 받지 못했습니다."
        contents.append(candidate.content)

        fn_calls = [
            p.function_call
            for p in candidate.content.parts
            if p.function_call is not None
        ]

        if not fn_calls:
            return "".join(
                p.text for p in candidate.content.parts
                if p.text is not None
            )

        fn_response_parts = []
        for fc in fn_calls:
            fn = TOOL_MAP.get(fc.name)
            args = dict(fc.args) if fc.args else {}
            result = fn(**args) if fn else f"알 수 없는 함수: {fc.name}"
            print(f"  [도구] {fc.name}({args})")
            fn_response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            )

        contents.append(types.Content(role="user", parts=fn_response_parts))

    return "최대 반복 횟수에 도달했습니다."


if __name__ == "__main__":
    test_query = """SELECT c.name, COUNT(o.id) as order_count, SUM(o.quantity) as total_qty
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE c.region = 'Seoul' AND o.status = 'delivered'
GROUP BY c.id
ORDER BY order_count DESC
LIMIT 10"""

    # 사람이 운영 DB에서 직접 실행한 EXPLAIN QUERY PLAN 결과를 여기에 붙여넣기
    test_explain = """QUERY PLAN
|--SCAN o
|--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
|--USE TEMP B-TREE FOR GROUP BY
`--USE TEMP B-TREE FOR ORDER BY"""

    print("=== SQL 최적화 에이전트 ===")
    print(f"분석 쿼리:\n{test_query}\n")
    print(f"실행 계획:\n{test_explain}\n")
    print("분석 중...\n")

    result = run_agent(test_query, test_explain)
    print("\n=== 최적화 제안 ===")
    print(result)