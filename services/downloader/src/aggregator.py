import pandas as pd

from .exceptions import PriceAggregationError

class HistoricalAggregator:
    _SUPPORTED_INTERVALS = {'1d':None, '1wk':"W-FRI", '2wk':"2W-FRI", '1mo':'ME', '2mo':'2ME', '3mo':'3ME'}
    
    @staticmethod
    def _reformat_dates(df:pd.DataFrame, interval:str='1mo'):
        dates = df.index
        if 'mo' in interval:
            dates = dates.strftime('%Y-%m')
        else:
            dates = dates.strftime('%Y-%m-%d')
        df.index = dates
        df.index.name = 'Date'
        return df

    def aggregate(self, df:pd.DataFrame, interval:str='1mo') -> pd.DataFrame:
        if df.empty:
            raise PriceAggregationError('Dataframe is empty')
        if interval not in self._SUPPORTED_INTERVALS:
            raise PriceAggregationError(f'Interval "{interval}" is not supported')
        if df.index.name != 'Date':
            raise PriceAggregationError('Index must be a named "Date"')
        if not isinstance(df.index, pd.DatetimeIndex):
            raise PriceAggregationError('Index must be of class pandas.DatetimeIndex.')
        if interval == '1d':
            to_return = df.copy()
            to_return['Price'] = to_return['Close']
        else:
            to_return = df.sort_index()
            to_return = (
                    to_return
                    .resample(self._SUPPORTED_INTERVALS[interval])
                    .agg(
                        Open=("Open", "first"),
                        High=("High", "max"),
                        Low=("Low", "min"),
                        Close=("Close", "last"),
                        Price=("Close", "mean"),
                        Volume=("Volume", "sum"),
                    )
                    .dropna(
                        subset=["Open", "High", "Low", "Close"],
                    )
                )
        to_return = self._reformat_dates(to_return, interval)
        return to_return
            

