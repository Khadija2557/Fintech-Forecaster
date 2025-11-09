import unittest
import pandas as pd
from models import forecast_arima, forecast_lstm
from utils import calculate_metrics

class TestModels(unittest.TestCase):
    def setUp(self):
        self.series = pd.Series([100, 102, 101, 103, 105, 104])  # Sample data

    def test_arima(self):
        pred = forecast_arima(self.series, 2)
        self.assertEqual(len(pred), 2)
        metrics = calculate_metrics(self.series[4:], pred[:2])  # Pseudo-val
        self.assertTrue('RMSE' in metrics)

    def test_lstm(self):
        pred = forecast_lstm(self.series, 2, time_steps=3)
        self.assertEqual(len(pred), 2)

if __name__ == '__main__':
    unittest.main()