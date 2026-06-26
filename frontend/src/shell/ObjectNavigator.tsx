import { CLOUD_MODULE_GROUPS } from "../navigation/cloudModules";

const STATUS_LABELS = {
  disabled: "Недоступно",
  planned: "Запланировано",
} as const;

type ObjectNavigatorProps = {
  activeView: string;
  capabilities: string[];
};

export function ObjectNavigator({ activeView, capabilities }: ObjectNavigatorProps) {
  return (
    <nav className="cloud-ui-object-navigator" aria-label="Объекты облака">
      <div className="cloud-ui-object-mode-strip" aria-label="Режимы навигации">
        <span aria-label="Hosts and clusters">▥</span>
        <span aria-label="VMs and templates">▦</span>
        <span aria-label="Storage">◉</span>
        <span aria-label="Networking">◇</span>
      </div>
      <div className="cloud-ui-object-tree">
        {CLOUD_MODULE_GROUPS.map((group) => (
          <section key={group.key} aria-label={group.title}>
            <h3>{group.title}</h3>
            <ul>
              {group.items.map((item) => {
                const reasonId = `cloud-ui-module-reason-${item.key}`;
                const missingCapability =
                  item.requiredCapability !== null &&
                  !capabilities.includes(item.requiredCapability);
                const canOpenImplementedModule =
                  item.status === "implemented" && !missingCapability;

                if (!canOpenImplementedModule) {
                  const disabledStatus: keyof typeof STATUS_LABELS =
                    item.status === "implemented"
                      ? "disabled"
                      : item.status === "disabled"
                        ? "disabled"
                        : "planned";
                  const reason =
                    item.status === "implemented" && missingCapability
                      ? `Требуется capability: ${item.requiredCapability}`
                      : item.reason;

                  return (
                    <li key={item.key}>
                      <span
                        className="cloud-ui-object-tree-item cloud-ui-object-tree-item-disabled"
                        aria-disabled="true"
                        aria-describedby={reasonId}
                        data-status={disabledStatus}
                      >
                        <span>{item.title}</span>
                        <span className="cloud-ui-object-tree-status">
                          {STATUS_LABELS[disabledStatus]}
                        </span>
                      </span>
                      <span id={reasonId} className="cloud-ui-object-tree-reason">
                        {reason}
                      </span>
                    </li>
                  );
                }

                return (
                  <li key={item.key}>
                    <a
                      className="cloud-ui-object-tree-item"
                      href={`?view=${encodeURIComponent(item.view)}`}
                      aria-current={activeView === item.view ? "page" : undefined}
                      data-status={item.status}
                    >
                      {item.title}
                    </a>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </nav>
  );
}
