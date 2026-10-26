"""어댑터 등록. 새 게시판을 만들면 여기 ADAPTERS에 추가."""
from ..base import Adapter
from .chemeng import ChemEngAdapter
from .engineering import EngineeringAdapter

ADAPTERS: dict[str, Adapter] = {
    "eng": EngineeringAdapter(),
    "chemeng": ChemEngAdapter(),
}
