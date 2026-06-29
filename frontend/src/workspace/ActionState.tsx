import type { WorkspaceAction } from "./types";
import { actionStateLabel } from "./types";

type ActionStateListProps = {
  title: string;
  actions: WorkspaceAction[];
};

export function ActionStateList({ actions, title }: ActionStateListProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={title}>
      <h3>{title}</h3>
      <ul className="cloud-ui-action-state-list">
        {actions.map((action) => (
          <li key={action.key} data-state={action.state}>
            <div>
              <strong>{action.title}</strong>
              <p className="cloud-ui-muted">{action.reason}</p>
            </div>
            <span className={`cloud-ui-badge cloud-ui-action-${action.state}`}>
              {actionStateLabel(action.state)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
