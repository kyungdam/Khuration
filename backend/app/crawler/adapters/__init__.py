"""어댑터 등록. 새 게시판을 만들면 여기 ADAPTERS에 추가."""
from ..base import Adapter
from .chemeng import ChemEngAdapter
from .engineering import EngineeringAdapter
from .main_site import MAIN_BOARDS

ADAPTERS: dict[str, Adapter] = {
    "eng": EngineeringAdapter(),
    "chemeng": ChemEngAdapter(),
    **MAIN_BOARDS,  # main, main_academic, main_scholarship, main_work
}
