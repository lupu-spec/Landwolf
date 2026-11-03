CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  goal TEXT NOT NULL,
  project TEXT NOT NULL DEFAULT '',
  runtime TEXT NOT NULL CHECK(runtime IN ('python','node','rust')),
  acceptance TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','review_ready','changes_requested','approved','cancelled')),
  archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
  revision INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_owner_created ON tasks(owner_id, created_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS task_results (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id),
  report TEXT NOT NULL,
  patch TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS results_task ON task_results(task_id, created_at DESC);
CREATE TABLE IF NOT EXISTS task_events (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id),
  kind TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_task ON task_events(task_id, created_at);
