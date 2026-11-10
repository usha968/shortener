import logging
import time

import clickhouse_connect
import redis

from app.config import get_settings
from app.events import COLUMNS, to_row

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("consumer")
GROUP, BATCH = "workers", 500


def run() -> None:
    cfg = get_settings()
    r = redis.Redis.from_url(cfg.redis_url, decode_responses=True)
    ch = clickhouse_connect.get_client(
        host=cfg.clickhouse_host,
        port=cfg.clickhouse_port,
        username="default",
        password=cfg.clickhouse_password,
    )
                                       username="default", password=cfg.clickhouse_password)
    try:
        r.xgroup_create(cfg.stream_name, GROUP, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    name = "consumer-1"
    read_id = "0"  # first re-read our unacknowledged entries, then switch to new ones (">")
    while True:
        resp = r.xreadgroup(GROUP, name, {cfg.stream_name: read_id}, count=BATCH, block=2000)
        entries = resp[0][1] if resp else []
        if not entries:
            read_id = ">"
            continue
        rows, ids = [], []
        for msg_id, fields in entries:
            ids.append(msg_id)
            try:
                rows.append(to_row(fields))
            except Exception:
                log.exception("dropping malformed event %s", msg_id)
        try:
            if rows:
                ch.insert("clicks", rows, column_names=COLUMNS)
        except Exception:
            log.exception("ClickHouse insert failed; will retry")
            time.sleep(5)
            read_id = "0"
            continue
        r.xack(cfg.stream_name, GROUP, *ids)


if __name__ == "__main__":
    run()
