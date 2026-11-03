CREATE TABLE portal_connections (
 id TEXT PRIMARY KEY,
 token_hash TEXT NOT NULL UNIQUE,
 owner_id TEXT NOT NULL,
 runner_id TEXT NOT NULL REFERENCES runners(id),
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1))
);
CREATE TABLE portal_dispatches (
 connection_id TEXT NOT NULL REFERENCES portal_connections(id),
 id TEXT NOT NULL,
 task_id TEXT NOT NULL UNIQUE REFERENCES tasks(id),
 payload_hash TEXT NOT NULL,
 created_at TEXT NOT NULL,
 PRIMARY KEY(connection_id,id)
);
