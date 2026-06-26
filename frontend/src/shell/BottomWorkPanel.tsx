const BOTTOM_PANEL_TABS = ["Recent Tasks", "Alarms", "Audit Tail", "Approvals"] as const;

export function BottomWorkPanel() {
  return (
    <section className="cloud-ui-bottom-panel" aria-label="Нижняя рабочая панель">
      <div className="cloud-ui-bottom-tabs" aria-label="Рабочие события">
        {BOTTOM_PANEL_TABS.map((tab, index) => (
          <button
            key={tab}
            type="button"
            aria-current={index === 0 ? "true" : undefined}
            className={index === 0 ? "cloud-ui-bottom-tab-active" : undefined}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="cloud-ui-bottom-empty">
        No active tasks · operation history remains available by correlation ID
      </div>
    </section>
  );
}
