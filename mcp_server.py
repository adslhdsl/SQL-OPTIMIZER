import sqlite3
import json
from mcp.server.fastmcp import FastMCP

DB_PATH = "sample.db"
mcp = FastMCP("SQL Optimizer")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def get_all_tables() -> str:
    """DB의 모든 테이블 목록을 반환합니다."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    return json.dumps([r["name"] for r in rows])


@mcp.tool()
def get_schema(table_name: str) -> str:
    """특정 테이블의 컬럼 구조를 반환합니다."""
    conn = get_conn()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    conn.close()
    if not rows:
        return f"테이블 '{table_name}' 을 찾을 수 없습니다."
    schema = [{"column": r["name"], "type": r["type"], "not_null": bool(r["notnull"]), "pk": bool(r["pk"])} for r in rows]
    return json.dumps(schema, ensure_ascii=False)


@mcp.tool()
def get_indexes(table_name: str) -> str:
    """특정 테이블의 인덱스 목록을 반환합니다."""
    conn = get_conn()
    indexes = conn.execute(
        f"PRAGMA index_list({table_name})"
    ).fetchall()
    result = []
    for idx in indexes:
        cols = conn.execute(f"PRAGMA index_info({idx['name']})").fetchall()
        result.append({
            "index_name": idx["name"],
            "unique": bool(idx["unique"]),
            "columns": [c["name"] for c in cols]
        })
    conn.close()
    if not result:
        return f"'{table_name}' 테이블에 인덱스가 없습니다."
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def run_explain(query: str) -> str:
    """쿼리의 실행 계획(EXPLAIN QUERY PLAN)을 반환합니다."""
    conn = get_conn()
    try:
        rows = conn.execute(f"EXPLAIN QUERY PLAN {query}").fetchall()
        conn.close()
        plan = [{"id": r["id"], "detail": r["detail"]} for r in rows]
        return json.dumps(plan, ensure_ascii=False)
    except Exception as e:
        conn.close()
        return f"오류: {str(e)}"


@mcp.tool()
def get_table_stats(table_name: str) -> str:
    """테이블의 행 수와 기본 통계를 반환합니다."""
    conn = get_conn()
    try:
        count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()["cnt"]
        conn.close()
        return json.dumps({"table": table_name, "row_count": count})
    except Exception as e:
        conn.close()
        return f"오류: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
