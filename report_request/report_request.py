import time
from abc import abstractmethod
from http import HTTPStatus
from typing import Dict

import aiohttp
import asyncio

from report import Report
from secrets import TOKEN, API_URL


class RequestStopperException(Exception):
    """
    Исключение которое будет вызвано, в случае превышения количество запросов.
    """

    def __init__(self, value, *args) -> None:
        super(RequestStopperException, self).__init__(*args)
        self.value = value

    def __repr__(self) -> str:
        return 'RequestStopperException is raised.'


class RequestStopper:
    """
    Создание ограничений по количеству запросов в секунду и минуту.
    """
    __timelines: Dict[str, str] = {
        'seconds': 'seconds',
        'minutes': 'minutes',
    }
    __seconds_in_timelines: Dict[str, int] = {
        __timelines['seconds']: 1,
        __timelines['minutes']: 60,
    }
    __counts_per: Dict[str, int] = {
        __timelines['seconds']: 0,
        __timelines['minutes']: 0,
    }
    __start_times_per: Dict[str, int] = {
        __timelines['seconds']: 0.0,
        __timelines['minutes']: 0.0,
    }
    __max_counts_per: Dict[str, int] = {
        __timelines['seconds']: 0,
        __timelines['minutes']: 0,
    }

    def _increment_requests_count(self) -> None:
        for timeline in self.__timelines:
            if type(self).__max_counts_per[timeline] == 0:
                continue
            if type(self).__counts_per[timeline] == 0:
                type(self).__start_times_per[timeline] = time.time()
            elif type(self).__counts_per[timeline] >= type(
                    self).__max_counts_per[timeline]:
                now_time = time.time()
                await_time = now_time - type(self).__start_times_per[timeline]
                if await_time < type(self).__seconds_in_timelines[timeline]:
                    raise RequestStopperException(value=await_time)
                else:
                    type(self).__start_times_per[timeline] = time.time()
                    type(self).__counts_per[timeline] = 0
            type(self).__counts_per[timeline] += 1

    def set_max_request_count(self, per_second: int = 0,
                              per_minute: int = 0) -> None:
        type(self).__max_counts_per['seconds'] = per_second
        type(self).__max_counts_per['minutes'] = per_minute


class ReportRequest(RequestStopper):
    """
    Асбтрактный метод создания запросов по API на сайт maximum-auto.ru.
    Опрос происходит согласно количеству максимальных запросов с задержкой.
    """
    delay_time: float = 0  # seconds
    api_url: str = API_URL
    url_prefix: str = None
    auth_type: str = 'Bearer'
    __token: str = TOKEN
    max_request_count_per_second: int = 0
    max_request_count_per_minute: int = 0

    def __init__(self) -> None:
        self.set_max_request_count(self.max_request_count_per_second,
                                   self.max_request_count_per_minute)
        if self.url_prefix is None:
            raise Exception('There is no url prefix.')

    def get_headers(self) -> dict:
        return {
            'Authorization': f'{self.auth_type} {self.__token}',
        }

    def get_full_url(self, request_id: int = None) -> str:
        url: str = self.api_url + self.url_prefix
        if request_id is not None:
            url += str(request_id)
        return url

    async def _make_request(self, *args, **kwargs) -> None:
        try:
            self._increment_requests_count()
            await self.request(*args, **kwargs)
        except RequestStopperException as err:
            await asyncio.sleep(err.value)

    @abstractmethod
    async def start(self, session: aiohttp.ClientSession) -> None:
        """
        Необходимо использовать метод _make_request вместо request, если
        требуется делать запросы по таймауту.
        """
        pass

    @abstractmethod
    async def request(self, session: aiohttp.ClientSession,
                      report: Report) -> None:
        pass

    @staticmethod
    def get_response_status(response: 'ClientResponse') -> int:
        if response.status == HTTPStatus.OK:
            return response.status
        elif response.status == HTTPStatus.CREATED:
            return response.status
        elif response.status == HTTPStatus.ACCEPTED:
            return response.status
        elif response.status == HTTPStatus.NO_CONTENT:
            return response.status
        elif response.status == HTTPStatus.UNAUTHORIZED:
            raise Exception('Авторизация не пройдена.')
        elif response.status == HTTPStatus.BAD_REQUEST:
            raise Exception('Тело запроса не соответствует спецификации.')
        elif response.status == HTTPStatus.CONFLICT:
            raise Exception('Отчет с таким id уже существует.')
        elif response.status == HTTPStatus.NOT_FOUND:
            raise Exception('Отчет с таким id не существует.')
        elif response.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise Exception('Превышен лимит.')
