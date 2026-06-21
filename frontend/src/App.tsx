import "@patternfly/react-core/dist/styles/base.css";

import {
  Alert,
  Bullseye,
  Button,
  Card,
  CardBody,
  CardTitle,
  Page,
  PageSection,
  Spinner,
  Title
} from "@patternfly/react-core";
import { type FormEvent, useEffect, useState } from "react";

import {
  type Capabilities,
  type HypervisorItem,
  type InstanceItem,
  type InventoryPage,
  type Readiness,
  type Subject,
  fetchCapabilities,
  fetchCurrentSession,
  fetchHypervisors,
  fetchInstances,
  fetchReadiness,
  login
} from "./api";
import "./styles.css";

const READINESS_UNAVAILABLE_MESSAGE = "Готовность API недоступна";
const SESSION_UNAVAILABLE_MESSAGE = "Сессия недоступна";
const CAPABILITIES_UNAVAILABLE_MESSAGE = "Список прав недоступен";

type InventoryView = "instances" | "hypervisors";

type LoadState =
  | { type: "loading" }
  | { type: "ready"; readiness: Readiness }
  | { type: "error"; message: string };

type AuthState =
  | { type: "loading" }
  | { type: "anonymous" }
  | {
      type: "authenticated";
      subject: Subject;
      capabilities: Capabilities | null;
      csrf: string | null;
    }
  | { type: "error"; message: string };

type InventoryState =
  | { type: "idle" }
  | { type: "loading"; view: InventoryView }
  | { type: "ready"; view: "instances"; page: InventoryPage<InstanceItem> }
  | { type: "ready"; view: "hypervisors"; page: InventoryPage<HypervisorItem> }
  | { type: "error"; view: InventoryView; message: string };

export function App() {
  const [state, setState] = useState<LoadState>({ type: "loading" });
  const [authState, setAuthState] = useState<AuthState>({ type: "loading" });
  const [inventoryState, setInventoryState] = useState<InventoryState>({ type: "idle" });
  const [locationSearch, setLocationSearch] = useState(() => window.location.search);
  const [loginName, setLoginName] = useState("");
  const [credential, setCredential] = useState("");

  const currentCapabilities =
    authState.type === "authenticated" ? authState.capabilities : null;
  const activeInventoryView =
    currentCapabilities === null
      ? null
      : resolveActiveInventoryView(currentCapabilities.capabilities, locationSearch);
  const capabilitySignature = currentCapabilities?.capabilities.join("|") ?? "";

  useEffect(() => {
    let mounted = true;

    fetchReadiness()
      .then((readiness) => {
        if (mounted) {
          setState({ type: "ready", readiness });
        }
      })
      .catch(() => {
        if (mounted) {
          setState({ type: "error", message: READINESS_UNAVAILABLE_MESSAGE });
        }
      });

    fetchCurrentSession()
      .then((session) => {
        if (!mounted) {
          return;
        }
        if (session === null) {
          setAuthState({ type: "anonymous" });
          return;
        }
        setAuthState({
          type: "authenticated",
          subject: session.subject,
          capabilities: null,
          csrf: null
        });
        fetchCapabilities()
          .then((capabilities) => {
            if (mounted) {
              setAuthState({
                type: "authenticated",
                subject: session.subject,
                capabilities,
                csrf: null
              });
            }
          })
          .catch(() => {
            if (mounted) {
              setAuthState({ type: "error", message: CAPABILITIES_UNAVAILABLE_MESSAGE });
            }
          });
      })
      .catch(() => {
        if (mounted) {
          setAuthState({ type: "error", message: SESSION_UNAVAILABLE_MESSAGE });
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    function handlePopState() {
      setLocationSearch(window.location.search);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (currentCapabilities === null || activeInventoryView === null) {
      setInventoryState({ type: "idle" });
      return;
    }

    let mounted = true;
    const params = new URLSearchParams(locationSearch);
    setInventoryState({ type: "loading", view: activeInventoryView });

    if (activeInventoryView === "instances") {
      fetchInstances(params)
        .then((page) => {
          if (mounted) {
            setInventoryState({ type: "ready", view: "instances", page });
          }
        })
        .catch(() => {
          if (mounted) {
            setInventoryState({
              type: "error",
              view: "instances",
              message: "Список ВМ недоступен"
            });
          }
        });
    } else {
      fetchHypervisors(params)
        .then((page) => {
          if (mounted) {
            setInventoryState({ type: "ready", view: "hypervisors", page });
          }
        })
        .catch(() => {
          if (mounted) {
            setInventoryState({
              type: "error",
              view: "hypervisors",
              message: "Список гипервизоров недоступен"
            });
          }
        });
    }

    return () => {
      mounted = false;
    };
  }, [activeInventoryView, capabilitySignature, currentCapabilities, locationSearch]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const loginResult = await login(loginName, credential);
      const capabilities = await fetchCapabilities();
      setAuthState({
        type: "authenticated",
        subject: loginResult.subject,
        capabilities,
        csrf: loginResult.csrf
      });
      setCredential("");
    } catch {
      setAuthState({ type: "error", message: "Не удалось выполнить вход" });
    }
  }

  function handleInventoryViewSelect(view: InventoryView) {
    const params = new URLSearchParams(locationSearch);
    params.set("view", view);
    params.delete("cursor");
    window.history.pushState({}, "", `${window.location.pathname}?${params.toString()}`);
    setLocationSearch(window.location.search);
  }

  return (
    <Page>
      <PageSection className="cloud-ui-page">
        <div className="cloud-ui-shell">
          <div className="cloud-ui-layout">
            <Title headingLevel="h1" size="xl">
              Портал OpenStack
            </Title>

            <div className="cloud-ui-status-grid">
              <Card className="cloud-ui-status-card">
                <CardTitle>Сессия</CardTitle>
                <CardBody>
                  {authState.type === "loading" && (
                    <Bullseye className="cloud-ui-loading">
                      <Spinner aria-label="Загрузка сессии" />
                    </Bullseye>
                  )}

                  {authState.type === "anonymous" && (
                    <form className="cloud-ui-login-form" onSubmit={handleLogin}>
                      <label>
                        <span>Логин</span>
                        <input
                          autoComplete="username"
                          onChange={(event) => setLoginName(event.target.value)}
                          type="text"
                          value={loginName}
                        />
                      </label>
                      <label>
                        <span>Код доступа</span>
                        <input
                          autoComplete="current-password"
                          onChange={(event) => setCredential(event.target.value)}
                          type="password"
                          value={credential}
                        />
                      </label>
                      <Button type="submit" variant="primary">
                        Войти
                      </Button>
                    </form>
                  )}

                  {authState.type === "error" && (
                    <Alert variant="danger" title={authState.message} />
                  )}

                  {authState.type === "authenticated" && (
                    <div className="cloud-ui-session">
                      <Alert variant="success" title={authState.subject.display_name} />
                      {authState.capabilities === null ? (
                        <Bullseye className="cloud-ui-compact-loading">
                          <Spinner aria-label="Загрузка прав" size="md" />
                        </Bullseye>
                      ) : (
                        hasSessionNavigation(authState.capabilities) && (
                          <nav aria-label="Разделы портала" className="cloud-ui-nav">
                            {authState.capabilities.capabilities.includes("operation.read") && (
                              <span className="cloud-ui-nav-item">Операции</span>
                            )}
                            {authState.capabilities.capabilities.includes("role.manage") && (
                              <span className="cloud-ui-nav-item">Управление ролями</span>
                            )}
                          </nav>
                        )
                      )}
                    </div>
                  )}
                </CardBody>
              </Card>

              <Card className="cloud-ui-status-card">
                <CardTitle>Статус сервиса</CardTitle>
                <CardBody>
                  {state.type === "loading" && (
                    <Bullseye className="cloud-ui-loading">
                      <Spinner aria-label="Загрузка готовности API" />
                    </Bullseye>
                  )}

                  {state.type === "error" && <Alert variant="danger" title={state.message} />}

                  {state.type === "ready" && (
                    <div className="cloud-ui-status-content">
                      <Alert
                        variant={state.readiness.status === "ok" ? "success" : "warning"}
                        title={`Готовность API: ${state.readiness.status}`}
                      />

                      <dl className="cloud-ui-dependencies" aria-label="Зависимости сервиса">
                        {Object.entries(state.readiness.dependencies).map(
                          ([name, dependency]) => (
                            <div className="cloud-ui-dependency-row" key={name}>
                              <dt>{name}</dt>
                              <dd>
                                {dependency.status} - {dependency.detail}
                              </dd>
                            </div>
                          )
                        )}
                      </dl>
                    </div>
                  )}
                </CardBody>
              </Card>
            </div>
          </div>

          {authState.type === "authenticated" && (
            <InventoryWorkArea
              activeView={activeInventoryView}
              capabilities={authState.capabilities}
              locationSearch={locationSearch}
              onInventoryViewSelect={handleInventoryViewSelect}
              state={inventoryState}
            />
          )}
        </div>
      </PageSection>
    </Page>
  );
}

function resolveActiveInventoryView(
  capabilities: string[],
  locationSearch: string
): InventoryView | null {
  const params = new URLSearchParams(locationSearch);
  const requestedView = params.get("view");
  const canReadInstances = capabilities.includes("instance.read");
  const canReadHypervisors = capabilities.includes("hypervisor.read");

  if (requestedView === "instances" && canReadInstances) {
    return "instances";
  }
  if (requestedView === "hypervisors" && canReadHypervisors) {
    return "hypervisors";
  }
  if (canReadInstances) {
    return "instances";
  }
  if (canReadHypervisors) {
    return "hypervisors";
  }
  return null;
}

function inventoryViewHref(view: InventoryView, locationSearch: string): string {
  const params = new URLSearchParams(locationSearch);
  params.set("view", view);
  params.delete("cursor");
  return `?${params.toString()}`;
}

function hasSessionNavigation(capabilities: Capabilities): boolean {
  return (
    capabilities.capabilities.includes("operation.read") ||
    capabilities.capabilities.includes("role.manage")
  );
}

function InventoryWorkArea({
  activeView,
  capabilities,
  locationSearch,
  onInventoryViewSelect,
  state
}: {
  activeView: InventoryView | null;
  capabilities: Capabilities | null;
  locationSearch: string;
  onInventoryViewSelect: (view: InventoryView) => void;
  state: InventoryState;
}) {
  if (capabilities === null) {
    return (
      <section aria-label="Инвентарь" className="cloud-ui-workarea">
        <Bullseye className="cloud-ui-loading">
          <Spinner aria-label="Загрузка прав инвентаря" />
        </Bullseye>
      </section>
    );
  }

  if (activeView === null) {
    return (
      <section aria-label="Инвентарь" className="cloud-ui-workarea">
        <Title headingLevel="h2" size="lg">
          Инвентарь
        </Title>
        <p className="cloud-ui-muted">Нет доступных разделов инвентаря.</p>
      </section>
    );
  }

  return (
    <section aria-label="Инвентарь" className="cloud-ui-workarea">
      <div className="cloud-ui-workarea-header">
        <InventoryNavigation
          activeView={activeView}
          capabilities={capabilities}
          locationSearch={locationSearch}
          onInventoryViewSelect={onInventoryViewSelect}
        />
        <Title headingLevel="h2" size="lg">
          {activeView === "instances" ? "Виртуальные машины" : "Список гипервизоров"}
        </Title>
      </div>

      {state.type === "loading" && state.view === activeView && (
        <Bullseye className="cloud-ui-loading">
          <Spinner aria-label="Загрузка инвентаря" />
        </Bullseye>
      )}

      {state.type === "error" && state.view === activeView && (
        <Alert variant="danger" title={state.message} />
      )}

      {state.type === "ready" &&
        state.view === "instances" &&
        activeView === "instances" &&
        renderInstancesPage(state.page)}

      {state.type === "ready" &&
        state.view === "hypervisors" &&
        activeView === "hypervisors" &&
        renderHypervisorsPage(state.page)}
    </section>
  );
}

function InventoryNavigation({
  activeView,
  capabilities,
  locationSearch,
  onInventoryViewSelect
}: {
  activeView: InventoryView;
  capabilities: Capabilities;
  locationSearch: string;
  onInventoryViewSelect: (view: InventoryView) => void;
}) {
  return (
    <nav aria-label="Разделы инвентаря" className="cloud-ui-nav">
      {capabilities.capabilities.includes("instance.read") && (
        <a
          aria-current={activeView === "instances" ? "page" : undefined}
          className="cloud-ui-nav-item"
          href={inventoryViewHref("instances", locationSearch)}
          onClick={(event) => {
            event.preventDefault();
            onInventoryViewSelect("instances");
          }}
        >
          ВМ
        </a>
      )}
      {capabilities.capabilities.includes("hypervisor.read") && (
        <a
          aria-current={activeView === "hypervisors" ? "page" : undefined}
          className="cloud-ui-nav-item"
          href={inventoryViewHref("hypervisors", locationSearch)}
          onClick={(event) => {
            event.preventDefault();
            onInventoryViewSelect("hypervisors");
          }}
        >
          Гипервизоры
        </a>
      )}
    </nav>
  );
}

function renderInventoryNotices<T>(page: InventoryPage<T>) {
  return (
    <div className="cloud-ui-inventory-notices" aria-label="Состояние данных">
      {page.partial && <span className="cloud-ui-badge cloud-ui-badge-warning">Частичные данные</span>}
      {page.freshness?.is_stale && (
        <span className="cloud-ui-badge cloud-ui-badge-stale">Данные устарели</span>
      )}
      {page.freshness?.observed_at && (
        <span className="cloud-ui-badge">Наблюдение: {formatUtc(page.freshness.observed_at)}</span>
      )}
      {page.warnings.map((warning) => (
        <span className="cloud-ui-warning-text" key={`${warning.source}:${warning.code}`}>
          {warning.detail}
        </span>
      ))}
    </div>
  );
}

function renderInstancesPage(page: InventoryPage<InstanceItem>) {
  return (
    <div className="cloud-ui-inventory-page">
      {renderInventoryNotices(page)}
      {page.items.length === 0 ? (
        <p className="cloud-ui-empty">Нет ВМ для выбранных фильтров.</p>
      ) : (
        <div className="cloud-ui-table-wrapper">
          <table className="cloud-ui-table" aria-label="Таблица ВМ">
            <thead>
              <tr>
                <th scope="col">Имя</th>
                <th scope="col">Статус</th>
                <th scope="col">Проект</th>
                <th scope="col">Узел</th>
                <th scope="col">Зона</th>
                <th scope="col">Наблюдение</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((item) => (
                <tr key={`${item.cloud_id}:${item.region_id}:${item.instance_id}`}>
                  <th scope="row">{item.name}</th>
                  <td>{item.status}</td>
                  <td>{item.project_id}</td>
                  <td>{formatNullable(item.host_name)}</td>
                  <td>{formatNullable(item.availability_zone)}</td>
                  <td>{formatUtc(item.observed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function renderHypervisorsPage(page: InventoryPage<HypervisorItem>) {
  return (
    <div className="cloud-ui-inventory-page">
      {renderInventoryNotices(page)}
      {page.items.length === 0 ? (
        <p className="cloud-ui-empty">Нет гипервизоров для выбранных фильтров.</p>
      ) : (
        <div className="cloud-ui-table-wrapper">
          <table className="cloud-ui-table" aria-label="Таблица гипервизоров">
            <thead>
              <tr>
                <th scope="col">Узел</th>
                <th scope="col">Статус сервиса</th>
                <th scope="col">Состояние</th>
                <th scope="col">vCPU</th>
                <th scope="col">ОЗУ</th>
                <th scope="col">Наблюдение</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((item) => (
                <tr key={`${item.cloud_id}:${item.region_id}:${item.hypervisor_id}`}>
                  <th scope="row">{item.host_name}</th>
                  <td>{item.service_status}</td>
                  <td>{item.service_state}</td>
                  <td>
                    {item.vcpus_used}/{item.vcpus_total}
                  </td>
                  <td>
                    {formatRam(item.ram_mb_used)} / {formatRam(item.ram_mb_total)}
                  </td>
                  <td>{formatUtc(item.observed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function formatNullable(value: string | null): string {
  return value ?? "-";
}

function formatRam(value: number): string {
  return `${Math.round(value / 1024)} ГиБ`;
}

function formatUtc(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return `${value} UTC`;
  }
  return `${date.toLocaleString("ru-RU", { timeZone: "UTC" })} UTC`;
}
