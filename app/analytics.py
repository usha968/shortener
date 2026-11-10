from datetime import date


def fetch_stats(ch, link_id: int, d_from: date, d_to: date, include_bots: bool) -> dict:
    """Synchronous; call via asyncio.to_thread. Queries run sequentially on one client."""
    where = ("link_id = {id:UInt64} AND ts >= toDateTime({f:Date}, 'UTC') "
             "AND ts < toDateTime({t:Date}, 'UTC') + INTERVAL 1 DAY")
    if not include_bots:
        where += " AND is_bot = 0"
    p = {"id": link_id, "f": d_from.isoformat(), "t": d_to.isoformat()}

    def rows(select_and_group: str):
        return ch.query(f"SELECT {select_and_group}", parameters=p).result_rows

    total, unique = rows(f"count(), uniqExact(visitor) FROM clicks WHERE {where}")[0]
    by_day = rows(f"toDate(ts) AS d, count() FROM clicks WHERE {where} GROUP BY d ORDER BY d")
    countries = rows(f"country, count() AS c FROM clicks WHERE {where} GROUP BY country ORDER BY c DESC LIMIT 10")
    devices = rows(f"device, count() FROM clicks WHERE {where} GROUP BY device")
    refs = rows(f"if(referrer = '', 'direct', referrer) AS r, count() AS c FROM clicks "
                f"WHERE {where} GROUP BY r ORDER BY c DESC LIMIT 10")
    return {
        "total_clicks": total,
        "unique_visitors": unique,
        "clicks_by_day": [{"date": d.isoformat(), "clicks": c} for d, c in by_day],
        "top_countries": [{"country": k, "clicks": c} for k, c in countries],
        "devices": {k: c for k, c in devices},
        "top_referrers": [{"source": k, "clicks": c} for k, c in refs],
    }
