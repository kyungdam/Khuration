"""화학공학과 학생광장 > 공지사항. 국제캠퍼스 단일 게시판."""
from .khu_cms import KhuCmsAdapter


class ChemEngAdapter(KhuCmsAdapter):
    name = "화학공학과"
    site = "https://chemeng.khu.ac.kr"
    board_path = "/chemeng/user/bbs/BMSR00040/"
    menu_no = "17600017"
