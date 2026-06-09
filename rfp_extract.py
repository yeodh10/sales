"""
Phase 7-A: RFP/제안요청서 PDF → 핵심 요구사항 추출 → 제품 대응표.

무료 경로(권장): 이 스크립트로 PDF 텍스트만 뽑아 data/rfp_extracted.txt 에 저장하고,
Claude Code에게 "rfp_extracted.txt 요구사항 추출하고 catalog.json으로 대응표 만들어줘"라고
요청한다. (API 키 불필요)

API 모드: --api 를 주면 Claude API로 바로 요구사항+대응표 JSON을 생성한다.

실행 예시:
    venv\\Scripts\\python.exe rfp_extract.py "C:\\path\\제안요청서.pdf"
    venv\\Scripts\\python.exe rfp_extract.py rfp.pdf --api
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import config  # noqa: F401  (.env 로드 + 콘솔 인코딩)

OUT_TXT = Path(__file__).parent / "data" / "rfp_extracted.txt"


def extract_text(pdf_path: str | Path) -> str:
    """PDF에서 텍스트를 추출한다(페이지 구분 표시 포함)."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        parts.append(f"\n----- [p.{i}] -----\n{text.strip()}")
    return "\n".join(parts).strip()


def analyze_rfp_api(text: str, catalog: list[dict]) -> dict:
    """(API 모드) Claude API로 요구사항 추출 + 제품 대응표 생성."""
    from anthropic import Anthropic

    client = Anthropic(api_key=config.require_anthropic_key())
    catalog_json = json.dumps(catalog, ensure_ascii=False, indent=2)
    system = (
        "당신은 공공조달 RFP를 분석하는 보안 솔루션 엔지니어입니다. "
        "제안요청서 본문에서 보안 관련 핵심 요구사항을 뽑고, 제공된 제품 카탈로그로 "
        "각 요구사항에 대응하는 제품과 대응방안을 매칭하세요. "
        '반드시 {"요구사항":[{"항목","원문근거","대응제품","대응방안"}]} JSON만 출력하세요.'
    )
    # 본문이 길 수 있어 앞부분 위주로 전달(데모 목적).
    body = text[:12000]
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": f"## 제품 카탈로그\n{catalog_json}\n\n## RFP 본문\n{body}"}],
    )
    out = "".join(b.text for b in resp.content if b.type == "text")
    s, e = out.find("{"), out.rfind("}")
    return json.loads(out[s : e + 1])


def main() -> int:
    parser = argparse.ArgumentParser(description="RFP PDF 요구사항 추출 (Phase 7-A)")
    parser.add_argument("pdf", help="제안요청서 PDF 경로")
    parser.add_argument("--api", action="store_true", help="Claude API로 대응표까지 생성")
    parser.add_argument("--out", default=str(OUT_TXT))
    args = parser.parse_args()

    if not Path(args.pdf).exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {args.pdf}")
        return 1

    try:
        text = extract_text(args.pdf)
    except Exception as e:  # noqa: BLE001
        print(f"[오류] PDF 텍스트 추출 실패: {e}")
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"[완료] 텍스트 {len(text):,}자 추출 → {out_path}")

    if not args.api:
        print(
            "\n다음 단계(무료): Claude Code에게 이렇게 요청하세요\n"
            f'  "data/{out_path.name} 의 보안 요구사항을 뽑고 catalog.json으로 대응표 만들어줘"'
        )
        return 0

    # API 모드
    import matcher  # load_catalog 재사용

    try:
        result = analyze_rfp_api(text, matcher.load_catalog())
    except Exception as e:  # noqa: BLE001
        print(f"[오류] API 분석 실패: {e}")
        return 1

    print("\n=== 요구사항 ↔ 제품 대응표 ===")
    for r in result.get("요구사항", []):
        print(f"\n· {r.get('항목','')}")
        print(f"   근거: {r.get('원문근거','')}")
        print(f"   대응: {r.get('대응제품','')} — {r.get('대응방안','')}")
    print("\n[완료] Phase 7-A: RFP 대응표 생성. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
