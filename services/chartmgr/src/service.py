from __future__ import annotations

from datetime import date, datetime

from .client import DownloaderApiClient, AnalyzerApiClient
from .exceptions import DownloaderResponseError, DownloaderClientError, InvalidDownloaderResponseError
from .schemas import ChartResponse, ChartRequest

class ChartMgrService:
    def __init__(self, downloader_client: DownloaderApiClient, 
                    analyzer_client: AnalyzerApiClient):
        self._downloader_client = downloader_client
        self._analyzer_client = analyzer_client
    
    @staticmethod
    def _validate_data(payload: list, expected: list[str]) -> None:
        if not isinstance(payload, list):
            raise DownloaderResponseError('Data format is not recognized. Must be a list.')
        if not payload:
            raise InvalidDownloaderResponseError('Data requested is empty.')
        for itm in payload:
            if not isinstance(itm, dict):
                raise InvalidDownloaderResponseError('Data object is not recognized. Objects must be dictionaries.')
            if not set(expected).issubset(itm):
                raise DownloaderResponseError('Some data missing required values.')
    
    async def _read_history(self, ticker, expected, *, period='10y', interval='1mo', 
                                auto_adjust=True, aggregate=True) -> list[dict]:
        request = ChartRequest(ticker, period=period, interval=interval, 
                                auto_adjust=auto_adjust, aggregate=aggregate)
        data = await self._downloader_client.price_history(request)

        self._validate_data(data, expected)

        return data
    
    @staticmethod
    def _format_data(data, expected, chart_type, title, xaxis_label, yaxis_label, legend):
        x_values = []
        y_values = {key: [] for key in expected[1:]}

        for row in data:
            x_values.append(row[expected[0]])
            for key in y_values:
                y_values[key].append(row[key])

        response_params = {'chart_type': chart_type, 'title': title, 
                            'xaxis_label': xaxis_label, 'yaxis_label': yaxis_label, 
                            'legend': legend, 'x_values': x_values, 'y_values': y_values}
        return ChartResponse(**response_params)
    
    async def get_price_history(self, ticker, *, period='10y', interval='1mo', 
                                auto_adjust=True, aggregate=True) -> ChartResponse:
        expected = ['Date', 'Open', 'High', 'Low', 'Close']
        data = await self._read_history(ticker, expected, period=period, interval=interval, 
                                        auto_adjust=auto_adjust, aggregate=aggregate)

        return self._format_data(data, expected, 'candlestick', 'Monthly OHLC', 'Date', 'Value', True)
    
    async def get_volume_history(self, ticker, *, period='10y', interval='1mo', 
                                auto_adjust=True, aggregate=True) -> ChartResponse:
        expected = ['Date', 'Volume']
        data = await self._read_history(ticker, expected, period=period, interval=interval, 
                                        auto_adjust=auto_adjust, aggregate=aggregate)
        
        return self._format_data(data, expected, 'bar', 'Monthly Volume', 'Date', 'Volume', True)