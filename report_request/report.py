import time
from collections import defaultdict, deque
from datetime import datetime


class ReportStatus:
    created: str = 'created'
    requested: str = 'requested'
    received: str = 'received'


class Report:
    """
    Класс описывающий состояние отчета. Хранит в себе количество созданных
    отчетов, а так же все отчеты в словаре, согласно статусам.
    """
    counts: int = 0
    reports: defaultdict = defaultdict(deque)

    def __init__(self) -> None:
        type(self).counts += 1
        self.id: int = self.counts
        self.request_time: datetime.timestamp = None
        self.status: str = ReportStatus.created
        self.value: str = ''
        self.reports[self.status].append(self)
        self.last_request_time: time.time = 0.0

    def __repr__(self) -> str:
        return f'Report {self.request_time};{self.id}'
