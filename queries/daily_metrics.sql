-- Daily marketing metrics by traffic source
-- Source: bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- Used by: src/data_fetcher.py

SELECT
  PARSE_DATE('%Y%m%d', event_date) AS date,
  traffic_source.source,
  traffic_source.medium,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNTIF(event_name = 'session_start') AS sessions,
  COUNTIF(event_name = 'page_view') AS page_views,
  COUNTIF(event_name = 'purchase') AS purchases,
  SUM(CASE WHEN event_name = 'purchase' THEN ecommerce.purchase_revenue ELSE 0 END) AS revenue
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '{start_date}' AND '{end_date}'
GROUP BY date, traffic_source.source, traffic_source.medium
ORDER BY date, sessions DESC
