CREATE TABLE IF NOT EXISTS users (
  id         BIGSERIAL PRIMARY KEY,
  email      TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
  id         BIGSERIAL PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES users(id),
  key_hash   TEXT UNIQUE NOT NULL,          -- sha256 of the key; the key itself is never stored
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE SEQUENCE IF NOT EXISTS link_id_seq;

CREATE TABLE IF NOT EXISTS links (
  id              BIGINT PRIMARY KEY DEFAULT nextval('link_id_seq'),
  public_id       TEXT UNIQUE NOT NULL,     -- lnk_xxxxxxxxxxxx, used in the API
  code            TEXT UNIQUE NOT NULL,     -- generated code or custom slug
  user_id         BIGINT NOT NULL REFERENCES users(id),
  original_url    TEXT NOT NULL,
  is_custom       BOOLEAN NOT NULL DEFAULT false,
  status          TEXT NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','disabled','blocked')),
  expires_at      TIMESTAMPTZ,
  click_limit     INTEGER CHECK (click_limit > 0),
  safety          TEXT NOT NULL DEFAULT 'unchecked'
                  CHECK (safety IN ('unchecked','safe','unsafe')),
  last_scanned_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS links_user_created_idx ON links (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS links_rescan_idx
  ON links (last_scanned_at NULLS FIRST) WHERE status = 'active';
