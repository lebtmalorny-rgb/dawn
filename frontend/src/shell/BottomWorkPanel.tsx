type BottomWorkPanelProps = {
  auditTailState?: "ready" | "planned";
  approvalsState?: "ready" | "planned";
};

const BOTTOM_PANEL_TABS = ["Recent Tasks", "Alarms", "Audit Tail", "Approvals"] as const;

export function BottomWorkPanel({
  auditTailState = "planned",
  approvalsState = "planned",
}: BottomWorkPanelProps) {
  return (
    <section className="cloud-ui-bottom-panel" aria-label="Нижняя рабочая панель">
      <div className="cloud-ui-bottom-tabs" aria-label="Рабочие события">
        {BOTTOM_PANEL_TABS.map((tab, index) => (
          <span
            key={tab}
            aria-current={index === 0 ? "true" : undefined}
            className={index === 0 ? "cloud-ui-bottom-tab-active" : undefined}
          >
            {tab}
          </span>
        ))}
      </div>
      <div className="cloud-ui-bottom-empty">
        No active tasks · operation history remains available by correlation ID
      </div>
      <div className="cloud-ui-bottom-planned">
        Audit Tail {auditTailState} · Approvals {approvalsState}
      </div>
    </section>
  );
}
