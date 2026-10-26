"""공과대학(국문) 공대마당 공지사항. 국제캠퍼스 단일 게시판."""
from .khu_cms import KhuCmsAdapter


class EngineeringAdapter(KhuCmsAdapter):
    name = "공과대학"
    site = "https://eng.khu.ac.kr"
    board_path = "/eng_kor/user/bbs/BMSR00040/"
    menu_no = "17100020"
