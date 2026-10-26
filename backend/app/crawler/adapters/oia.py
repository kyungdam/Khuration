"""국제처 국제교류팀(oia.khu.ac.kr) 게시판. 공과대학과 같은 CMS 구조.
캠퍼스별 게시판이 따로 없고 글마다 "공통" 등 표시만 붙는다.
Incoming Program(외국인 교환학생 대상)과 Partner University Program(글이 드묾, 대부분 대학원)은 넣지 않았다."""
from .khu_cms import KhuCmsAdapter


class OiaAdapter(KhuCmsAdapter):
    site = "https://oia.khu.ac.kr"
    board_path = "/oiak_kor/user/bbs/BMSR00040/"


OIA_BOARDS = {
    "oia": OiaAdapter("국제교류처(공지)", "5800010"),
    "oia_outgoing": OiaAdapter("국제교류처(파견 프로그램)", "5800012"),
}
