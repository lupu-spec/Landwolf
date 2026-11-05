CREATE TABLE releases (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), owner_id TEXT NOT NULL,
 runner_id TEXT NOT NULL REFERENCES runners(id), project_key TEXT NOT NULL,
 result_id TEXT NOT NULL REFERENCES task_results(id), result_sha256 TEXT NOT NULL,
 task_revision INTEGER NOT NULL, version TEXT NOT NULL, selected_files TEXT NOT NULL,
 target TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued', operation TEXT NOT NULL DEFAULT 'build',
 stage TEXT NOT NULL DEFAULT 'queued', message TEXT NOT NULL DEFAULT 'WAITING FOR RUNNER',
 operation_seq INTEGER NOT NULL DEFAULT 1, previous_sha256 TEXT,
 revision INTEGER NOT NULL DEFAULT 1, lease TEXT, lease_until TEXT, deadline TEXT,
 artifact_sha256 TEXT, source_sha256 TEXT, source_base64 TEXT,
 manifest TEXT NOT NULL DEFAULT '{}', report TEXT NOT NULL DEFAULT '{}',
 preview_url TEXT, production_url TEXT, previous_id TEXT, previous_version TEXT,
 finish_hash TEXT, delivered_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(owner_id,runner_id,project_key,version)
);
CREATE INDEX releases_task ON releases(task_id,created_at);
CREATE UNIQUE INDEX one_active_release_project ON releases(runner_id,project_key)
 WHERE state IN ('queued','building','publish_queued','publishing','rollback_queued','rolling_back');
CREATE TABLE release_events (
 id TEXT PRIMARY KEY, release_id TEXT NOT NULL REFERENCES releases(id),
 revision INTEGER NOT NULL, state TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(release_id,revision)
);
