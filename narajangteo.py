"""
나라장터(조달청) 입찰공고정보서비스 클라이언트.

공공데이터포털 데이터셋 15129394:
  https://www.data.go.kr/data/15129394/openapi.do

엔드포인트:
  http://apis.data.go.kr/1230000/BidPublicInfoService/<오퍼레이션>

업무구분별로 오퍼레이션이 분리돼 있다(물품/용역/공사/외자).
보안 솔루션은 주로 '용역'(보안관제·정보보호 서비스), '물품'(보안 장비)에서 나온다.

주의: 공공데이터포털에서 활용신청 후 발급받은 인증키가 필요하다(.env의
DATA_GO_KR_SERVICE_KEY). 일부 계정/버전에서 엔드포인트 베이스가 다를 수 있으니
정상 응답이 안 오면 포털의 Swagger 명세에서 오퍼레이션 경로를 재확인할 것.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

import requests

import config

BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

# 업무구분 한글명 -> (오퍼레이션, inqryDiv 기본값)
# inqryDiv: 1=공고일시 기준 조회(공식 가이드 예시 기준)
BUSINESS_DIVISIONS = {
    "물품": "getBidPblancListInfoThng",
    "용역": "getBidPblancListInfoServc",
    "공사": "getBidPblancListInfoCnstwk",
    "외자": "getBidPblancListInfoFrgcpt",
}


@dataclass
class Bid:
    """입찰공고 한 건. API 응답에서 필요한 핵심 필드만 추린다."""

    공고번호: str
    공고명: str
    공고기관: str
    수요기관: str
    공고일시: str
    마감일시: str
    업무구분: str
    공고url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _fmt_dt(dt: datetime) -> str:
    """yyyyMMddHHmm 형식 (나라장터 조회 파라미터 형식)."""
    return dt.strftime("%Y%m%d%H%M")


def search_bids(
    division: str = "용역",
    keyword: Optional[str] = None,
    days: int = 7,
    begin_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
    rows: int = 100,
    page: int = 1,
    timeout: int = 20,
) -> list[Bid]:
    """
    입찰공고 목록을 조회한다.

    Args:
        division: 업무구분 한글명 (물품/용역/공사/외자)
        keyword: 공고명 키워드 필터(bidNtceNm). None이면 전체.
        days: end_dt 기준 최근 며칠. begin_dt/end_dt를 직접 주면 무시됨.
        begin_dt, end_dt: 조회 기간 직접 지정(우선).
        rows: 페이지당 행 수.
        page: 페이지 번호.

    Returns:
        Bid 리스트.

    Raises:
        ValueError: 잘못된 업무구분.
        RuntimeError: 인증키 미설정 또는 API 오류.
    """
    if division not in BUSINESS_DIVISIONS:
        raise ValueError(
            f"알 수 없는 업무구분: {division!r}. "
            f"가능: {list(BUSINESS_DIVISIONS)}"
        )

    service_key = config.require_data_go_kr_key()
    operation = BUSINESS_DIVISIONS[division]

    if end_dt is None:
        end_dt = datetime.now()
    if begin_dt is None:
        begin_dt = end_dt - timedelta(days=days)

    # 주의: 이 오퍼레이션은 공고명(bidNtceNm) 서버 필터를 무시하고 날짜 범위
    # 전체를 돌려준다. 따라서 키워드 필터는 받아온 뒤 클라이언트에서 처리한다.
    # 키워드가 있으면 충분히 많이 받아와서 걸러야 하므로 numOfRows를 키운다.
    api_rows = max(rows, 500) if keyword else rows

    params = {
        "serviceKey": service_key,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": _fmt_dt(begin_dt),
        "inqryEndDt": _fmt_dt(end_dt),
        "pageNo": str(page),
        "numOfRows": str(api_rows),
    }

    url = f"{BASE_URL}/{operation}"

    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"나라장터 API 호출 실패: {e}") from e

    try:
        data = resp.json()
    except ValueError as e:
        # 인증키 오류 등은 XML 에러를 돌려주기도 한다.
        snippet = resp.text[:300]
        raise RuntimeError(
            f"JSON 파싱 실패(인증키/요청 형식 확인 필요). 응답 일부:\n{snippet}"
        ) from e

    bids = _parse_response(data, division)

    # 클라이언트측 키워드 필터(공고명 부분일치, 공백 무시).
    if keyword:
        kw = keyword.replace(" ", "")
        bids = [b for b in bids if kw in b.공고명.replace(" ", "")]
        bids = bids[:rows]

    return bids


def _parse_response(data: dict, division: str) -> list[Bid]:
    """공공데이터포털 표준 응답(response.header/body) 파싱."""
    response = data.get("response", {})
    header = response.get("header", {})
    result_code = header.get("resultCode")

    # 정상: "00" 또는 "0". 그 외는 오류 메시지를 올린다.
    if result_code not in (None, "00", "0"):
        msg = header.get("resultMsg", "(메시지 없음)")
        raise RuntimeError(f"API 오류 [{result_code}] {msg}")

    body = response.get("body", {})
    items = body.get("items", [])

    # items는 [] 또는 [{...}] 또는 {"item": [...]} 형태로 올 수 있다.
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):  # 단건이면 dict 하나
        items = [items]
    if items is None:
        items = []

    bids: list[Bid] = []
    for it in items:
        bids.append(
            Bid(
                공고번호=str(it.get("bidNtceNo", "")).strip(),
                공고명=str(it.get("bidNtceNm", "")).strip(),
                공고기관=str(it.get("ntceInsttNm", "")).strip(),
                수요기관=str(it.get("dminsttNm", "")).strip(),
                공고일시=str(it.get("bidNtceDt", "")).strip(),
                마감일시=str(it.get("bidClseDt", "")).strip(),
                업무구분=division,
                공고url=str(it.get("bidNtceDtlUrl", it.get("bidNtceUrl", ""))).strip(),
            )
        )
    return bids
