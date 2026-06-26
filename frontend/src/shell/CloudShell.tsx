import type { ReactNode } from "react";

import type { ShellContext } from "../navigation/types";
import { BottomWorkPanel } from "./BottomWorkPanel";
import { ObjectNavigator } from "./ObjectNavigator";
import { TopChrome } from "./TopChrome";

type CloudShellProps = {
  context: ShellContext;
  activeView: string;
  objectTitle: string;
  objectType: string;
  tabs: string[];
  children: ReactNode;
};

export function CloudShell({
  context,
  activeView,
  objectTitle,
  objectType,
  tabs,
  children,
}: CloudShellProps) {
  return (
    <div className="cloud-ui-shell-v2">
      <TopChrome context={context} />
      <div className="cloud-ui-shell-body">
        <ObjectNavigator activeView={activeView} />
        <main className="cloud-ui-workbench" id="main-content">
          <div className="cloud-ui-object-header">
            <div className="cloud-ui-object-icon" aria-hidden="true">
              ▥
            </div>
            <div>
              <h1>{objectTitle}</h1>
              <p>
                {objectType} · {context.freshnessLabel}
              </p>
            </div>
            <button type="button" className="cloud-ui-actions-button">
              ⋮ Actions
            </button>
          </div>
          <nav className="cloud-ui-object-tabs" aria-label="Разделы объекта">
            {tabs.map((tab, index) => (
              <button key={tab} type="button" role="tab" aria-selected={index === 0}>
                {tab}
              </button>
            ))}
          </nav>
          <div className="cloud-ui-workbench-content">{children}</div>
          <BottomWorkPanel />
        </main>
      </div>
    </div>
  );
}
