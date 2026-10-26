"""공지 URL 정규화: 같은 공지는 세션·추적·목록 파라미터가 달라도 같은 URL (= 한 번만 저장)."""
from app.crawler.adapters.aladdin import detail_url as aladdin_url
from app.crawler.adapters.engineering import EngineeringAdapter
from app.crawler.adapters.main_site import MAIN_BOARDS
from app.crawler.adapters.oia import OIA_BOARDS
from app.crawler.adapters.urls import normalize_url

ENG = "https://eng.khu.ac.kr/eng_kor/user/bbs/BMSR00040/view.do?menuNo=17100020&boardId=557542"
ALADDIN = ("https://aladdin.khu.ac.kr/portfolio/ptfol/imng/icmpNsbjtPgm/"
           "findIcmpNsbjtPgmInfo.do?encSddpbSeq=f0127b8880173ddf1712aa3d60d318c0")


def test_noise_params_are_dropped():
    assert normalize_url(ENG + "&pageIndex=3&searchKeyword=&searchCondition=1#top") == ENG
    assert normalize_url(ENG.replace("view.do", "view.do;jsessionid=ABC123") + "&utm_source=kakao&fbclid=x") == ENG
    assert normalize_url("HTTPS://ENG.KHU.AC.KR" + ENG[len("https://eng.khu.ac.kr"):]) == ENG
    assert normalize_url(ALADDIN + "&paginationInfo.currentPageNo=2&paramStart=paramStart&ssoReChk=ok") == ALADDIN


def test_already_clean_urls_stay_identical():
    """이미 저장된 공지 URL이 바뀌면 한 번씩 중복 저장되므로, 깨끗한 URL은 글자 하나 안 바뀌어야 한다."""
    assert EngineeringAdapter().detail_url("557542") == ENG
    assert aladdin_url("f0127b8880173ddf1712aa3d60d318c0") == ALADDIN
    assert normalize_url(ENG) == ENG  # 파라미터 순서(menuNo → boardId) 유지
    assert OIA_BOARDS["oia_outgoing"].detail_url("556358").endswith("view.do?menuNo=5800012&boardId=556358")


def test_main_site_tabs_share_one_url_per_notice():
    """대표 홈페이지는 탭(menuNo)이 달라도 boardId가 같으면 같은 글 → 일반 탭 주소 하나로"""
    urls = {ad.detail_url("323410") for ad in MAIN_BOARDS.values()}
    assert urls == {"https://www.khu.ac.kr/kor/user/bbs/BMSR00040/view.do?menuNo=200316&boardId=323410"}
    assert MAIN_BOARDS["main_scholarship"].list_url.endswith("menuNo=200318")  # 목록은 각 탭 그대로
