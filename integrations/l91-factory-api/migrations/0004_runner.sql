CREATE TABLE runners (
 id TEXT PRIMARY KEY, owner_id TEXT, name TEXT NOT NULL,
 token_hash TEXT NOT NULL UNIQUE, pair_hash TEXT UNIQUE,
 pair_expires TEXT, created_at TEXT NOT NULL, registration_ip TEXT NOT NULL,
 last_seen TEXT, capabilities TEXT NOT NULL DEFAULT '[]', ready INTEGER NOT NULL DEFAULT 0,
 issue TEXT NOT NULL DEFAULT '', revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX runners_owner ON runners(owner_id, revoked);
CREATE INDEX runners_registration ON runners(registration_ip, created_at);
ALTER TABLE tasks ADD COLUMN runner_id TEXT REFERENCES runners(id);
ALTER TABLE tasks ADD COLUMN project_key TEXT NOT NULL DEFAULT '';
ALTER TABLE task_results ADD COLUMN source TEXT NOT NULL DEFAULT 'manual_import';
CREATE TABLE task_runs (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
 owner_id TEXT NOT NULL, runner_id TEXT NOT NULL REFERENCES runners(id),
 state TEXT NOT NULL CHECK(state IN ('queued','running','completed','failed','cancelled')),
 stage TEXT NOT NULL DEFAULT 'queued', message TEXT NOT NULL DEFAULT '',
 lease TEXT, lease_until TEXT, deadline TEXT, result_hash TEXT,
 created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
 sequence INTEGER NOT NULL,
 UNIQUE(task_id, sequence)
);
CREATE UNIQUE INDEX one_active_task_run ON task_runs(task_id) WHERE state IN ('queued','running');
CREATE UNIQUE INDEX one_running_job ON task_runs(runner_id) WHERE state='running';
CREATE INDEX runner_queue ON task_runs(runner_id, state, created_at);
