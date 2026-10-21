# Dataset Inspection Report

Generated: 2026-10-21T05:01:12.131188+00:00
Data root: `/Users/biswajit.brahma/my_claudecode/research/dalu/data`

This report is generated entirely from the files actually present on disk. No filenames, column names, labels, or sampling intervals were assumed in advance.

## Source: microsoft_cloud_monitoring

### `cloud_monitoring_sample.csv`
- Format: csv
- Rows: 710, Columns: 3
- Columns: ['TimeStamp', 'Value', 'Label']
- Dtypes: {'TimeStamp': 'str', 'Value': 'int64', 'Label': 'int64'}
- Timestamp column: TimeStamp
  - Time range: 2018-06-19 00:00:00 to 2018-07-18 00:00:00
  - Inferred sampling interval (mode): 0 days 01:00:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 13
- Duplicate full rows: 13
- Missing values by column: none
- Label column: Label
  - Label value counts: {'0': 616, '1': 94}
- Service/host identifier: None
- Notes:
  - No explicit service/host identifier column found.
  - Univariate series: single 'Value' column, hourly cadence, binary Label column present.

## Source: kaggle_cloud_resource_usage

### `kaggle_cloud_resource_usage.csv`
- Format: csv
- Rows: 10080, Columns: 10
- Columns: ['time', 'node_cpu_utilization|Average|node1', 'node_cpu_utilization|Average|node2', 'pod_memory_utilization|Average|carts-db', 'pod_network_rx_bytes|Average|user', 'carts_req_rate', 'user_req_rate', 'orders_perc95_rt', 'front-end_perc95_rt', 'anomaly']
- Dtypes: {'time': 'str', 'node_cpu_utilization|Average|node1': 'float64', 'node_cpu_utilization|Average|node2': 'float64', 'pod_memory_utilization|Average|carts-db': 'float64', 'pod_network_rx_bytes|Average|user': 'float64', 'carts_req_rate': 'float64', 'user_req_rate': 'float64', 'orders_perc95_rt': 'float64', 'front-end_perc95_rt': 'float64', 'anomaly': 'int64'}
- Timestamp column: time
  - Time range: 2024-05-13 15:53:00+00:00 to 2024-05-20 15:52:00+00:00
  - Inferred sampling interval (mode): 0 days 00:01:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: anomaly
  - Label value counts: {'0': 9309, '1': 771}
- Service/host identifier: None
- Notes:
  - Possible service/host identifying columns present: ['node_cpu_utilization|Average|node1', 'node_cpu_utilization|Average|node2', 'pod_memory_utilization|Average|carts-db', 'pod_network_rx_bytes|Average|user'] (embedded as multivariate feature names, not a row-level identifier column).
  - Multivariate series: column names encode metric|aggregation|entity (e.g. 'node_cpu_utilization|Average|node1'), suggesting multiple nodes/services were pivoted into one wide row per minute. Row-level 'anomaly' label is a single global flag, not per-entity, and does not indicate fault type.

## Source: aws_cloudwatch_metrics

### `aws_cloudwatch_metrics/ec2_cpu_utilization_24ae8d.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-02-14 14:30:00 to 2014-02-28 14:25:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_24ae8d
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_53ea38.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-02-14 14:30:00 to 2014-02-28 14:25:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_53ea38
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_5f5533.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-02-14 14:27:00 to 2014-02-28 14:22:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_5f5533
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_77c1ca.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-02 14:25:00 to 2014-04-16 14:20:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_77c1ca
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_825cc2.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-10 00:04:00 to 2014-04-24 00:09:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 2
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_825cc2
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_ac20cd.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-02 14:29:00 to 2014-04-16 14:49:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 2
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_ac20cd
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_c6585a.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-02 14:29:00 to 2014-04-16 14:24:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_c6585a
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_cpu_utilization_fe7f93.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-02-14 14:27:00 to 2014-02-28 14:22:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_cpu_utilization_fe7f93
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_disk_write_bytes_1ef3de.csv`
- Format: csv
- Rows: 4730, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-03-01 17:34:00 to 2014-03-18 03:39:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 1
  - Duplicate timestamps: 11
- Duplicate full rows: 11
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_disk_write_bytes_1ef3de
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_disk_write_bytes_c0d644.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-02 14:25:00 to 2014-04-16 14:20:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_disk_write_bytes_c0d644
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_network_in_257a54.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-10 00:04:00 to 2014-04-24 00:09:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 2
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_network_in_257a54
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/ec2_network_in_5abac7.csv`
- Format: csv
- Rows: 4730, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-03-01 17:36:00 to 2014-03-18 03:41:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 1
  - Duplicate timestamps: 11
- Duplicate full rows: 6
- Missing values by column: none
- Label column: None
- Service/host identifier: ec2_network_in_5abac7
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/elb_request_count_8c0756.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-10 00:04:00 to 2014-04-24 00:39:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 8
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: elb_request_count_8c0756
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/grok_asg_anomaly.csv`
- Format: csv
- Rows: 4621, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-01-16 00:00:00 to 2014-02-01 01:00:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: grok_asg_anomaly
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/iio_us-east-1_i-a2eb1cd9_NetworkIn.csv`
- Format: csv
- Rows: 1243, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2013-10-09 16:25:00 to 2013-10-13 23:55:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: iio_us-east-1_i-a2eb1cd9_NetworkIn
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/rds_cpu_utilization_cc0c53.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-02-14 14:30:00 to 2014-02-28 14:30:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 1
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: rds_cpu_utilization_cc0c53
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.

### `aws_cloudwatch_metrics/rds_cpu_utilization_e47b3b.csv`
- Format: csv
- Rows: 4032, Columns: 2
- Columns: ['timestamp', 'value']
- Dtypes: {'timestamp': 'str', 'value': 'float64'}
- Timestamp column: timestamp
  - Time range: 2014-04-10 00:02:00 to 2014-04-23 23:57:00
  - Inferred sampling interval (mode): 0 days 00:05:00
  - Gaps > 1.5x modal interval: 0
  - Duplicate timestamps: 0
- Duplicate full rows: 0
- Missing values by column: none
- Label column: None
- Service/host identifier: rds_cpu_utilization_e47b3b
- Notes:
  - No label/anomaly/fault column detected by name heuristics.
  - FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' corpus, not a fresh export described as coming from the user's own experimental environment. No label/combined_windows.json file was found alongside these CSVs, so these files are currently UNLABELED. This should be confirmed with the user before being described as 'AWS CloudWatch metrics and logs exported from my experimental environment' in the dissertation.
