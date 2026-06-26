import { CLOUD_MODULE_GROUPS } from "../navigation/cloudModules";

type ObjectNavigatorProps = {
  activeView: string;
};

export function ObjectNavigator({ activeView }: ObjectNavigatorProps) {
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
              {group.items.map((item) => (
                <li key={item.key}>
                  <a
                    href={`?view=${encodeURIComponent(item.view)}`}
                    aria-current={activeView === item.view ? "page" : undefined}
                    data-status={item.status}
                  >
                    {item.title}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </nav>
  );
}
