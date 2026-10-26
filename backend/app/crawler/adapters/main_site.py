"""경희대 대표 홈페이지(www.khu.ac.kr) 공지사항. 탭(일반·학사·장학·근로)마다 menuNo가 다른 게시판이다.
서울·국제 캠퍼스 게시판이 따로 있지 않고, 한 게시판에서 글마다 서울/국제/공통 표시만 붙는다
(그래서 어댑터를 캠퍼스로 나누지 않고, 표시는 본문 첫 줄 "캠퍼스: …"로 넘긴다).
시간표 변경·교내학점교류·행사 탭은 앱 대상(학사·장학·공모전)과 거리가 있어 넣지 않았다."""
from .khu_cms import KhuCmsAdapter, parse_detail_board02


class MainSiteAdapter(KhuCmsAdapter):
    site = "https://www.khu.ac.kr"
    board_path = "/kor/user/bbs/BMSR00040/"
    list_rows = "table tbody tr"
    canonical_menu_no = "200316"  # 탭이 달라도 같은 boardId면 같은 공지 → 일반 탭 주소로 통일
    parse_detail = staticmethod(parse_detail_board02)


MAIN_BOARDS = {
    "main": MainSiteAdapter("경희대 공지(일반)", "200316"),
    "main_academic": MainSiteAdapter("경희대 공지(학사)", "200317"),
    "main_scholarship": MainSiteAdapter("경희대 공지(장학)", "200318"),
    "main_work": MainSiteAdapter("경희대 공지(근로)", "200361"),
}
