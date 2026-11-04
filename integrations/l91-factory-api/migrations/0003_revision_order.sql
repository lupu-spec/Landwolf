-- Timestamps are presentation data; task revisions define commit order.
ALTER TABLE task_events ADD COLUMN task_revision INTEGER NOT NULL DEFAULT 0;
ALTER TABLE task_results ADD COLUMN task_revision INTEGER NOT NULL DEFAULT 0;

-- Preserve insertion order for artifacts saved before revision tracking.
UPDATE task_events SET task_revision = (
  SELECT COUNT(*) FROM task_events earlier
  WHERE earlier.task_id = task_events.task_id AND earlier.rowid <= task_events.rowid
);
UPDATE task_results SET task_revision = (
  SELECT COUNT(*) FROM task_results earlier
  WHERE earlier.task_id = task_results.task_id AND earlier.rowid <= task_results.rowid
);
CREATE UNIQUE INDEX events_task_revision ON task_events(task_id, task_revision);
CREATE UNIQUE INDEX results_task_revision ON task_results(task_id, task_revision);
