import datetime
import pytest
import polars as pl
from baseline_pl.aggregated_features_baseline.features_aggregator import get_top_values
from baseline_pl.aggregated_features_baseline.calculators import StatsFeaturesCalculator

@pytest.fixture()
def events():
    max_date = datetime.datetime.fromisoformat("2025-02-01")
    dates = [max_date - datetime.timedelta(days=r) for r in range(-8,0)]
    df = pl.DataFrame(
        {
            "client_id": [1,1,2,2,3,3, 4,4],
            "timestamp": dates,
            "sku": [1,1,5,1,2,3,2,4],
            "category": [6,6,5,6,4,3,4,1],
         }
    )
    return df

def test_get_top_values(events):
    
    actual = get_top_values(events, ["sku", "category"], 2)
    expected = {'category': [6, 4], 'sku': [1, 2]}
    assert expected==actual


@pytest.fixture()
def stats_feature_calculator(events):
    top_values = get_top_values(events, ["sku", "category"], 2)
    max_date = events.get_column("timestamp").max()
    sfc = StatsFeaturesCalculator(
        num_days = [1,7], 
        max_date=max_date,
        columns = ["sku", "category"],
        unique_values = top_values,
    )
    return sfc
    
def test_stats_feature_calculator(events, stats_feature_calculator):
    features = stats_feature_calculator.compute_features(events)
    breakpoint()

