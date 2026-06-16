"""
Phase 4: 에이전트화 (tool use).

사용자의 자연어 요청을 받으면 Claude가 스스로 `search_bids` 도구를 호출해
공고를 가져오고, 이후 분류 → 매칭 → 토킹포인트 파이프라인을 돌려 브리핑한다.

여기서 '에이전트'란 자율 로봇이 아니라, Claude가 필요한 도구를 스스로 호출하며
여러 단계를 처리하는 워크플로를 뜻한다.

실행 예시:
    venv\\Scripts\\python.exe agent.py "이번 달 정보보호 관련 용역 공고 찾아서 매칭해줘"
    venv\\Scripts\\python.exe agent.py --sample "이번 주 보안 공고 정리해줘"
"""

from __future__ import annotations

import argparse
import json
import sys

import config
import narajangteo
import pipeline

# Claude에게 노출할 도구 정의.
SEARCH_BIDS_TOOL = {
    "name": "search_bids",
    "description": (
        "나라장터(조달청) 입찰공고를 검색한다. 업무구분/키워드/기간으로 최근 공고 "
        "목록을 가져온다. 보안 관련 공고를 찾을 때 사용한다."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "division": {
                "type": "string",
                "enum": list(narajangteo.BUSINESS_DIVISIONS),
                "description": "업무구분. 보안 서비스는 보통 '용역', 보안 장비는 '물품'.",
            },
            "keyword": {
                "type": "string",
                "description": "공고명 키워드(예: 정보보호, 보안관제, 방화벽). 없으면 생략.",
            },
            "days": {
                "type": "integer",
                "description": "최근 며칠 범위. '이번 주'≈7, '이번 달'≈30.",
            },
        },
        "required": ["division"],
    },
}


def _run_search_tool(tool_input: dict, sample: bool) -> list[dict]:
    """search_bids 도구 실제 실행."""
    return pipeline.get_bids(
        sample=sample,
        division=tool_input.get("division", "용역"),
        keyword=tool_input.get("keyword"),
        days=int(tool_input.get("days", 14)),
    )


def run_agent(user_request: str, sample: bool = False, max_turns: int = 4) -> dict:
    """
    자연어 요청을 받아 도구 호출 → 파이프라인 실행.

    Returns:
        pipeline.run_pipeline 결과 dict. 도구를 한 번도 못 부르면 빈 결과.
    """
    client = config.make_anthropic_client()

    system = (
        "당신은 공공기관 보안 영업을 돕는 에이전트입니다. 사용자의 요청을 보고 "
        "필요하면 search_bids 도구를 호출해 입찰공고를 가져오세요. "
        "보안 영업이 목적이므로 정보보호/보안 관련 키워드와 적절한 업무구분을 고르세요."
    )
    messages: list[dict] = [{"role": "user", "content": user_request}]

    fetched: list[dict] = []

    for _ in range(max_turns):
        resp = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            tools=[SEARCH_BIDS_TOOL],
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": resp.content})

        # 응답에 포함된 '모든' tool_use 블록을 처리해야 한다.
        # (하나라도 빠뜨리면 Anthropic API 가 다음 turn 에서
        #  tool_use_id 누락으로 400 오류를 낸다.)
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "search_bids":
                print(f"  [도구 호출] search_bids({json.dumps(block.input, ensure_ascii=False)})")
                try:
                    result = _run_search_tool(block.input, sample)
                    fetched = result  # 마지막 검색 결과를 파이프라인 입력으로 사용
                    content = f"{len(result)}건의 공고를 가져왔습니다."
                except Exception as e:  # noqa: BLE001 - 도구 오류를 모델에 전달해 복구 유도
                    content = f"검색 실패: {e}"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                            "is_error": True,
                        }
                    )
                    continue
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    }
                )
            else:
                # 알 수 없는 도구도 반드시 tool_result 로 응답해야 루프가 깨지지 않는다.
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"알 수 없는 도구: {block.name}",
                        "is_error": True,
                    }
                )

        # 방어: tool_use 블록이 하나도 없으면(이상 응답) 무한 루프를 막기 위해 종료.
        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})

    if not fetched:
        return {"classified": [], "security": [], "matched": [],
                "talking_points": [], "briefing": []}

    return pipeline.run_pipeline(fetched)


def main() -> int:
    parser = argparse.ArgumentParser(description="보안 영업 에이전트 (Phase 4)")
    parser.add_argument("request", help="자연어 요청 (예: '이번 달 정보보호 용역 공고 찾아줘')")
    parser.add_argument("--sample", action="store_true", help="예시 공고로 실행")
    args = parser.parse_args()

    print(f"\n요청: {args.request}\n")
    try:
        out = run_agent(args.request, sample=args.sample)
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1

    sec = [r for r in out["briefing"] if r["보안여부"]]
    if not out["briefing"]:
        print("공고를 가져오지 못했습니다. 요청을 더 구체적으로 적어보세요.")
        return 0

    print(f"\n보안 관련 공고 {len(sec)}건:\n")
    for r in sec:
        print(f"🔒 [{r['카테고리']}] {r['공고명']}")
        for p in r["추천제품"]:
            print(f"   · {p['제품명']} — {p['매칭이유']}")
        if r["토킹포인트"]:
            print(f"   💬 {r['토킹포인트']}")
        print()

    print("[완료] Phase 4: 에이전트 tool use 정상 동작. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
