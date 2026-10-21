# Preprocessing Report: kaggle

- Rows in (post raw-read): 10080
- Rows after cleaning: 10080
- Exact duplicate rows dropped: 0
- Duplicate timestamps remaining after dedup: 0
- Rows dropped for unparseable timestamp: 0
- Inferred sampling interval: 0 days 00:01:00
- Gaps exceeding 1.5x modal interval: 0 (NOT interpolated)
- Missing values by column (pre feature engineering): none
- Time range: 2024-05-13 15:53:00+00:00 to 2024-05-20 15:52:00+00:00

- Rows dropped due to incomplete lag/rolling features (leading rows): 14
- Rows dropped at split boundaries to prevent window leakage: 30
- Feature count: 72
- Split sizes: train=6039, val=1998, test=1999
- Has labels: True
- Training-split anomaly fraction: 0.0810
  - NOTE: training split is NOT anomaly-free. The detector is trained on data that may contain anomalies; this is disclosed rather than assumed away.
