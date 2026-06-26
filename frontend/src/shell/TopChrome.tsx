import type { ShellContext } from "../navigation/types";

type TopChromeProps = {
  context: ShellContext;
};

export function TopChrome({ context }: TopChromeProps) {
  return (
    <header className="cloud-ui-top-chrome" role="banner">
      <button
        className="cloud-ui-icon-button"
        type="button"
        aria-label="Меню продукта запланировано для следующего этапа"
        title="Меню продукта запланировано для следующего этапа"
        disabled
      >
        ☰
      </button>
      <div className="cloud-ui-product-title">{context.productTitle}</div>
      <label className="cloud-ui-global-search">
        <span className="cloud-ui-sr-only">Глобальный поиск</span>
        <input
          aria-label="Глобальный поиск"
          type="search"
          placeholder={context.searchPlaceholder}
        />
      </label>
      <button
        className="cloud-ui-icon-button"
        type="button"
        aria-label="Обновление данных запланировано для следующего этапа"
        title="Обновление данных запланировано для следующего этапа"
        disabled
      >
        ↻
      </button>
      <div className="cloud-ui-shell-meta">{context.scopeLabel}</div>
      <div className="cloud-ui-shell-meta">{context.policyRevision}</div>
      <div className="cloud-ui-shell-user">{context.identityLabel}</div>
    </header>
  );
}
