import type { SecondaryNavigationSection } from "./types";

type SecondaryNavigationProps = {
  activeItem: string;
  ariaLabel: string;
  sections: SecondaryNavigationSection[];
};

export function SecondaryNavigation({ activeItem, ariaLabel, sections }: SecondaryNavigationProps) {
  return (
    <nav className="cloud-ui-secondary-nav" aria-label={ariaLabel}>
      {sections.map((section) => (
        <section key={section.key} className="cloud-ui-secondary-nav-section">
          <h4>{section.title}</h4>
          <ul>
            {section.items.map((item) => (
              <li key={item}>
                <span aria-current={item === activeItem ? "page" : undefined}>{item}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </nav>
  );
}
