import type { ObjectEventRow, ObjectEventTableState } from "./types";

type ObjectEventTableProps = {
  title: string;
  rows: ObjectEventRow[];
  state: ObjectEventTableState;
};

export function ObjectEventTable({ rows, state, title }: ObjectEventTableProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={title}>
      <div className="cloud-ui-workspace-panel-header">
        <h3>{title}</h3>
        <button type="button" disabled>
          Export {state.exportState}
        </button>
      </div>
      <div className="cloud-ui-table-toolbar" aria-label={`${title} table state`}>
        <span>{state.filterLabel}</span>
        <span>{state.sortLabel}</span>
        <span>Page size {state.pageSize}</span>
        <span>{state.totalItems} events</span>
      </div>
      <p className="cloud-ui-muted">{state.exportReason}</p>
      <div className="cloud-ui-table-scroll">
        <table className="cloud-ui-object-event-table" aria-label={`${title} table`}>
          <thead>
            <tr>
              <th scope="col">Description</th>
              <th scope="col">Type</th>
              <th scope="col">Date Time</th>
              <th scope="col">Task</th>
              <th scope="col">Target</th>
              <th scope="col">User</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  <details>
                    <summary>{row.description}</summary>
                    <code>{row.correlationId}</code>
                  </details>
                </td>
                <td>{row.type}</td>
                <td>{row.dateTime}</td>
                <td>{row.task}</td>
                <td>
                  <a href={`#${row.id}`}>{row.targetLabel}</a>
                </td>
                <td>{row.userLabel}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
