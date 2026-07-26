import pandas as pd

from .exceptions import PriceAggregationError

class HistoricalAggregator:
    _SUPPORTED_INTERVALS = {'1d':None, '1wk':"W-FRI", '2wk':"2W-FRI", '1mo':'ME', '2mo':'2ME', '3mo':'3ME'}
    
    @staticmethod
    def _reformat_dates(df:pd.DataFrame, interval:str='1mo') -> pd.DataFrame:
        """
        helper method to make dates more intuitive.

        Args:
            df (pd.DataFrame): the dataframe to be reformatted
            interval (str): The interval to be reported. one of product(['1', '2', '3', ...], ['d', 'wk', 'mo', 'y'])
                            e.g.: "3d" -> (jan 1, jan 2, jan 3), (jan 4, jan 5, jan 6), ... -> jan 3, jan 6, ...
                                  "1mo" -> (jan 1, jan 2, jan 3...), (feb 1, feb 2, ...)... -> jan 31, feb 28, ...
                                  "2mo" -> (jan 1, jan2, ... feb 1, feb 2...), (mar 1, ..., apr 1, ...), ... -> feb 28, apr 30
        
        Returns:
            pd.DataFrame: The formatted dataframe
        """
        dates = df.index
        if 'mo' in interval:
            dates = dates.strftime('%Y-%m')
        else:
            dates = dates.strftime('%Y-%m-%d')
        df.index = dates
        df.index.name = 'Date'
        return df

    def aggregate(self, df:pd.DataFrame, interval:str='1mo') -> pd.DataFrame:
        """
        OHLC aggregator for requested interval; turning the interval into a "day"

        Args:
            df (pd.DataFrame): the data to be aggregated
            interval (str):  The interval to be reported. one of product(['1', '2', '3', ...], ['d', 'wk', 'mo', 'y'])
                            e.g.: "3d" -> (jan 1, jan 2, jan 3), (jan 4, jan 5, jan 6), ... -> jan 3, jan 6, ...
                                  "1mo" -> (jan 1, jan 2, jan 3...), (feb 1, feb 2, ...)... -> jan 31, feb 28, ...
                                  "2mo" -> (jan 1, jan2, ... feb 1, feb 2...), (mar 1, ..., apr 1, ...), ... -> feb 28, apr 30
        
        Returns:
            pd.DataFrame: the new dataframe of aggregated data
        """
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
            

