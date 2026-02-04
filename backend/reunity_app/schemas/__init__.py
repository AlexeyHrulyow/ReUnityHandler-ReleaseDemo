# Экспортируем все схемы
from .auth import *
from .doctor import *
from .patient import *
# Импортируем только если файлы существуют
try:
    from .case import *
except ImportError:
    pass

try:
    from .document import *
except ImportError:
    pass