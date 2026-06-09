"""
Phase 0 검증용 스크립트.
.env에서 Anthropic API 키를 읽어 Claude에 간단한 메시지를 보내고 응답을 출력한다.

실행:
    venv\\Scripts\\python.exe hello_claude.py
"""

import os
import sys

from dotenv import load_dotenv

# Windows 콘솔에서 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 고정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# .env 로드
load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()


def main() -> int:
    # 1) 키 확인
    if not API_KEY or API_KEY.startswith("sk-ant-여기에"):
        print("[오류] ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("       .env 파일을 열어 실제 키를 입력한 뒤 다시 실행해 주세요.")
        print("       키 발급: https://console.anthropic.com")
        return 1

    # 2) SDK import (설치 누락 시 안내)
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[오류] anthropic 패키지가 없습니다.")
        print("       venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 1

    client = Anthropic(api_key=API_KEY)

    print(f"[정보] 모델 {MODEL} 에 메시지를 보냅니다...\n")

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": "안녕하세요! 한 문장으로 자기소개를 해주세요.",
                }
            ],
        )
    except Exception as e:  # noqa: BLE001 - 셋업 단계에서는 모든 예외를 친절히 안내
        print(f"[오류] API 호출에 실패했습니다: {e}")
        print("       키가 올바른지, 네트워크 연결이 되는지 확인해 주세요.")
        return 1

    # 3) 응답 출력
    text = "".join(block.text for block in resp.content if block.type == "text")
    print("─" * 50)
    print("Claude 응답:")
    print(text)
    print("─" * 50)
    print(
        f"\n[성공] 토큰 사용량 - 입력 {resp.usage.input_tokens}, "
        f"출력 {resp.usage.output_tokens}"
    )
    print("[완료] Phase 0 셋업이 정상 동작합니다. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
