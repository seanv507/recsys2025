import datetime
import numpy as np
import pandas as pd
import polars as pl
import re

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List

from baseline_pl.aggregated_features_baseline.constants import (
    EMBEDDINGS_DTYPE,
)


def raise_err_if_incorrect_form(string_representation_of_vector: str):
    """
    Checks if string_representation_of_vector has the correct form.

    Correct form is a string representing list of ints with arbitrary number of spaces in between.

    Args:
        string_representation_of_vector (str): potential string representation of vector
    """
    m = re.fullmatch(r"\[( *\d* *)*\]", string=string_representation_of_vector)
    if m is None:
        raise ValueError(
            f"{string_representation_of_vector} is incorrect form of string representation of vector – correct form is: '[( *\d* *)*]'"
        )


def parse_to_array(string_representation_of_vector: str) -> np.ndarray:
    """
    Parses string representing vector of integers into array of integers.

    Args:
        string_representation_of_vector (str): string representing vector of ints e.g. '[11 2 3]'
    Returns:
        np.ndarray: array of integers obtained from string representation
    """
    raise_err_if_incorrect_form(
        string_representation_of_vector=string_representation_of_vector
    )
    string_representation_of_vector = string_representation_of_vector.replace(
        "[", ""
    ).replace("]", "")
    return np.array(
        [int(s) for s in string_representation_of_vector.split(" ") if s != ""]
    ).astype(dtype=EMBEDDINGS_DTYPE)


class Calculator(ABC):
    """
    Calculator interface for computing features and storing their size.
    """

    @property
    @abstractmethod
    def features_size(self) -> int:
        """
        Calculates features size for calculator.
        """
        pass

    @abstractmethod
    def compute_features(self, events: pl.DataFrame) -> np.ndarray:
        """
        This method computes features for a single collection of events.

        Args:
            events (pd.DataFrame): DataFrame containing the events data.
        Returns:
            np.ndarray: feature vector
        """
        pass


class QueryFeaturesCalculator(Calculator):
    """
    Calculator class for computing query features for a search_query event type.
    The feature vector is the average of all query embeddings from search_query events in user's history.
    """

    def __init__(self, query_column: str, single_query: str):
        """
        Args:
            query_column (str): Name of column containing quantized text embeddings.
            single_query (str): A sample string representation of quantized (integer) text embedding vector.
        """
        self.query_column = query_column
        self.query_size = len(parse_to_array(single_query))

    @property
    def features_size(self) -> int:
        return self.query_size

    def compute_features(self, events: pd.DataFrame) -> np.ndarray:
        quantized_query_representations = np.stack(
            [
                parse_to_array(string_representation_of_vector=v)
                for v in events.get_column(self.query_column).to_numpy()
            ],
            axis=0,
        )
        return quantized_query_representations.mean(axis=0)


class StatsFeaturesCalculator(Calculator):
    """
    Calculator class for computing statistical features for a given event type.
    The feature vector includes the count of occurrences of specified column values within given time windows in user's history.
    Multiple time windows and columns combination can be used to create features.
    """

    def __init__(
        self,
        num_days: List[int],
        max_date: datetime.datetime,
        columns: List[str],
        unique_values: dict[str, list],
    ):
        """
        Args:
            num_days (List[int]): List of time windows (in days) for generating features.
            max_date (datetime): The latest event date in the training input data.
            columns (List[str]): Columns to be used for feature generation.
            unique_values (Dict[List]): A dictionary with each key being a column name and
            the corresponding value being a list of selected
            number of top values for that column.
        """
        self._num_days = num_days
        self._max_date = max_date
        self._columns = columns
        self._unique_values = unique_values

    @property
    def features_size(self) -> int:
        return (
            sum((len(self._unique_values[column]) for column in self._columns))
            * len(self._num_days)
            + 1
        )

    def compute_features(self, events: pl.DataFrame) -> np.ndarray:
        features = np.zeros(self.features_size, dtype=EMBEDDINGS_DTYPE)
        features[0] = events.shape[0]
        pointer = 1
        # todo assert timestamp is increasing
        timestamps = events.get_column("timestamp")
        for days in self._num_days:
            start_date = self._max_date - timedelta(days=days)
            idx = timestamps.search_sorted(start_date)
            for column in self._columns:
                features_to_write = features[
                    pointer : pointer + len(self._unique_values[column])
                ]

                counts = dict(
                    events
                    .select(column)
                    [idx:]
                    .filter(pl.col(column).is_in(self._unique_values[column]))
                    .to_series(0)
                    .value_counts()
                    .iter_rows()
                )
                
                features[pointer : pointer + len(self._unique_values[column])] = [counts.get(val,0) for val in self._unique_values[column]]
                pointer += len(self._unique_values[column])
        return features
