import polars as pl
import logging

from data_utils.data_dir import DataDir

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def join_properties(
    event_df: pl.DataFrame, properties_df: pl.DataFrame
) -> pl.DataFrame:
    """
    This function joins product properties for each event in event_df.
    Args:
        event_df (pl.DataFrame): DataFrame storing events to which properties are joined.
        properties_df (pl.DataFrame): DataFrame with product properties, that should be
        joined to event_df.
    Returns:
        pl.DataFrame: events DataFrame with product properties.
    """
    joined_df = event_df.join(properties_df, on="sku", validate="m:1")
    assert joined_df.select(pl.all_horizontal(pl.all().is_not_null().all())).item(0,0), "Missing sku in properties_df"
    return joined_df


def load_with_properties(data_dir: DataDir, event_type: str) -> pl.DataFrame:
    """
    This function load dataset for given event type. If event type admits sku column, then product properties are joined.
    Args:
        data_dir (DataDir): The DataDir class where Paths to raw event data, input and targte folders are stored.
        event_type (str): Name of the event.
    Returns:
        pl.DataFrame: events DataFrame with product joined properties if available.
    """
    event_df = pl.read_parquet(data_dir.input_dir / f"{event_type}.parquet")
    if event_type not in ["page_visit", "search_query"]:
        properties_df = pl.read_parquet(data_dir.properties_file)
        return join_properties(event_df=event_df, properties_df=properties_df)
    return event_df
