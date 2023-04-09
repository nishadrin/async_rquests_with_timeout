import asyncio
import time
from datetime import datetime, timezone
from http import HTTPStatus

import aiofiles
import aiohttp

from report import Report, ReportStatus
from report_request import ReportRequest


class CreateReport(ReportRequest):
    """
    Создания запроса отчета на сайте за каждые delay_time секунд.
    """
    delay_time: float = 60  # seconds
    url_prefix: str = '/reports'
    max_request_count_per_second: int = 5
    max_request_count_per_minute: int = 50

    async def start(self, session: aiohttp.ClientSession) -> None:
        while True:
            await self._make_request(session, Report())
            await asyncio.sleep(self.delay_time)

    async def request(self, session: aiohttp.ClientSession,
                      report: Report) -> None:
        data = {'id': str(report.id)}
        async with session.post(self.get_full_url(), headers=self.get_headers(),
                                json=data) as response:
            if self.get_response_status(response) == HTTPStatus.CREATED:
                self.handler_success_request(report)

    @staticmethod
    def handler_success_request(report: Report) -> None:
        report.request_time = datetime.timestamp(datetime.now(timezone.utc))
        report.status = ReportStatus.requested
        Report.reports[ReportStatus.requested].append(report)


class GetReport(ReportRequest):
    """
    Создание запроса отчета один раз за каждые delay_time секунд.
    """
    delay_time: float = 0.1  # seconds
    url_prefix: str = '/reports/'
    max_request_count_per_second: int = 20

    async def start(self, session: aiohttp.ClientSession) -> None:
        while True:
            if Report.reports[ReportStatus.requested]:
                report = Report.reports[ReportStatus.requested].popleft()
                if self.is_time_to_request(report):
                    await self._make_request(session, report)
                else:
                    Report.reports[ReportStatus.requested].append(report)
                    await asyncio.sleep(self.delay_time)

            await asyncio.sleep(0)

    def is_time_to_request(self, report):
        difference: float = time.time() - report.last_request_time
        if report.last_request_time == 0.0 or difference > self.delay_time:
            return True
        return False

    async def request(self, session: aiohttp.ClientSession,
                      report: Report) -> None:
        async with session.get(self.get_full_url(report.id),
                               headers=self.get_headers()) as response:
            report.last_request_time = time.time()
            if self.get_response_status(response) == HTTPStatus.OK:
                self.handler_success_request(report, await response.json())
            else:
                Report.reports[ReportStatus.requested].append(report)

    @staticmethod
    def handler_success_request(report: Report, data: dict) -> None:
        if report.id == int(data['id']):
            report.value = data['value']
            Report.reports[ReportStatus.received].append(report)
        else:
            raise Exception('Не совпадает id очтета.')


class ReportToCSV:
    """
    Сохранение отчета в файл csv.
    """
    delay_time: int = 0
    filename: str = 'results.csv'
    file_mode: str = 'a'

    @staticmethod
    def get_text(report) -> str:
        return f'{report.request_time};{report.value}\n'

    async def start(self, file) -> None:
        while True:
            if Report.reports[ReportStatus.received]:
                report = Report.reports[ReportStatus.received].popleft()
                await file.write(self.get_text(report))
            await asyncio.sleep(self.delay_time)


async def main() -> None:
    request_classes = [
        CreateReport(),
        GetReport(),
    ]
    tasks = []

    async with aiohttp.ClientSession() as session:
        async with aiofiles.open(ReportToCSV.filename,
                                 mode=ReportToCSV.file_mode) as file:
            for request_class in request_classes:
                tasks.append(asyncio.create_task(request_class.start(session)))
            tasks.append(asyncio.create_task(ReportToCSV().start(file)))

            await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
