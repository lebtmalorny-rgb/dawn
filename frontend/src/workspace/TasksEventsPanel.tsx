type TasksEventsPanelProps = {
  objectId: string;
};

export function TasksEventsPanel({ objectId }: TasksEventsPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label="Tasks and events">
      <h3>Object task timeline</h3>
      <p className="cloud-ui-muted">
        Operation timeline and audit links will be correlated by object ID and request ID.
      </p>
      <code>{objectId}</code>
    </section>
  );
}
