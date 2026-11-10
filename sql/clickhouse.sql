CREATE TABLE IF NOT EXISTS default.clicks (
  ts       DateTime('UTC'),
  link_id  UInt64,
  country  LowCardinality(String),
  city     String,
  device   LowCardinality(String),
  browser  LowCardinality(String),
  os       LowCardinality(String),
  referrer LowCardinality(String),
  is_bot   UInt8,
  visitor  String                -- daily-salted hash, not an IP
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (link_id, ts)
TTL ts + INTERVAL 13 MONTH;
