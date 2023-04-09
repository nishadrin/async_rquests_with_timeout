from http import HTTPStatus

import aiohttp
import asyncio

from report import Report
from report_request import ReportRequest


class DeleteReport(ReportRequest):
    delay_time: int = 0  # seconds
    url_prefix: str = '/reports/'

    async def start(self, session: aiohttp.ClientSession) -> None:
        for i in range(100):
            report = Report()
            await self.request(session, report)
        await asyncio.sleep(self.delay_time)

    async def request(self, session: aiohttp.ClientSession,
                      report: Report) -> None:
        async with session.delete(self.get_full_url(report.id),
                                  headers=self.get_headers()) as response:
            if self.get_response_status(response) == HTTPStatus.NO_CONTENT:
                print(f'Удален отчет id №{report.id}')


async def main():
    async with aiohttp.ClientSession() as session:
        await DeleteReport().start(session)


if __name__ == '__main__':
    asyncio.run(main())
