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
  Title,
} from "@patternfly/react-core";
import { type FormEvent, useEffect, useState } from "react";

import {
  type Capabilities,
  type GroupMember,
  type GroupPreviewResponse,
  type ResourceGroup,
  type HypervisorItem,
  type InstanceItem,
  type InventoryModuleDescriptor,
  type InventoryPage,
  type Readiness,
  type Subject,
  fetchCapabilities,
  fetchCurrentSession,
  fetchGroup,
  fetchGroupMembers,
  fetchGroups,
  fetchHypervisors,
  fetchInstances,
  fetchInventoryModules,
  fetchReadiness,
  login,
  previewGroupRule,
} from "./api";
import "./styles.css";

const READINESS_UNAVAILABLE_MESSAGE = "Готовность API недоступна";
const SESSION_UNAVAILABLE_MESSAGE = "Сессия недоступна";
const CAPABILITIES_UNAVAILABLE_MESSAGE = "Список прав недоступен";

type PortalView = "inventory" | "groups";
type InventoryView = "instances" | "hypervisors";
type Density = "compact" | "comfortable";
type InstanceColumnKey =
  | "name"
  | "status"
  | "project_id"
  | "host_name"
  | "hypervisor_id"
  | "availability_zone"
  | "observed_at";
type HypervisorColumnKey =
  | "host_name"
  | "service_status"
  | "service_state"
  | "running_vms"
  | "capacity"
  | "availability_zone"
  | "observed_at";

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

type GroupState =
  | { type: "idle" }
  | { type: "loading" }
  | { type: "ready"; groups: ResourceGroup[] }
  | { type: "error"; message: string };

type GroupDetailState =
  | { type: "idle" }
  | { type: "loading"; groupId: string }
  | { type: "ready"; group: ResourceGroup; members: GroupMember[] }
  | { type: "error"; groupId: string; message: string };

type MemberSearchState =
  | { type: "idle" }
  | { type: "loading" }
  | { type: "instances"; page: InventoryPage<InstanceItem> }
  | { type: "hypervisors"; page: InventoryPage<HypervisorItem> }
  | { type: "error"; message: string };

type PreviewState =
  | { type: "idle" }
  | { type: "loading" }
  | { type: "ready"; response: GroupPreviewResponse }
  | { type: "error"; message: string };

type InventoryModulesState =
  | { type: "idle" }
  | { type: "loading" }
  | { type: "ready"; modules: InventoryModuleDescriptor[] }
  | { type: "error"; message: string };

const INVENTORY_MODULES_UNAVAILABLE_MESSAGE = "Модули inventory недоступны";

const INSTANCE_COLUMN_KEYS = [
  "name",
  "status",
  "project_id",
  "host_name",
  "hypervisor_id",
  "availability_zone",
  "observed_at",
] as const;
const DEFAULT_INSTANCE_COLUMNS: InstanceColumnKey[] = [
  "name",
  "status",
  "project_id",
  "host_name",
  "hypervisor_id",
  "availability_zone",
  "observed_at",
];
const INSTANCE_COLUMN_LABELS: Record<InstanceColumnKey, string> = {
  name: "Имя",
  status: "Статус",
  project_id: "Проект",
  host_name: "Узел",
  hypervisor_id: "Гипервизор",
  availability_zone: "Зона",
  observed_at: "Наблюдение",
};

const HYPERVISOR_COLUMN_KEYS = [
  "host_name",
  "service_status",
  "service_state",
  "running_vms",
  "capacity",
  "availability_zone",
  "observed_at",
] as const;
const DEFAULT_HYPERVISOR_COLUMNS: HypervisorColumnKey[] = [
  "host_name",
  "service_status",
  "service_state",
  "running_vms",
  "capacity",
  "observed_at",
];
const HYPERVISOR_COLUMN_LABELS: Record<HypervisorColumnKey, string> = {
  host_name: "Узел",
  service_status: "Статус сервиса",
  service_state: "Состояние",
  running_vms: "ВМ",
  capacity: "Емкость",
  availability_zone: "Зона",
  observed_at: "Наблюдение",
};

const INVENTORY_FILTER_KEYS = [
  "q",
  "project_id",
  "status",
  "host_name",
  "hypervisor_id",
  "availability_zone",
  "service_status",
  "service_state",
  "maintenance_status",
] as const;

export function App() {
  const [state, setState] = useState<LoadState>({ type: "loading" });
  const [authState, setAuthState] = useState<AuthState>({ type: "loading" });
  const [inventoryState, setInventoryState] = useState<InventoryState>({
    type: "idle",
  });
  const [inventoryModulesState, setInventoryModulesState] =
    useState<InventoryModulesState>({
      type: "idle",
    });
  const [groupState, setGroupState] = useState<GroupState>({ type: "idle" });
  const [groupDetailState, setGroupDetailState] = useState<GroupDetailState>({
    type: "idle",
  });
  const [locationSearch, setLocationSearch] = useState(
    () => window.location.search,
  );
  const [loginName, setLoginName] = useState("");
  const [credential, setCredential] = useState("");

  const currentCapabilities =
    authState.type === "authenticated" ? authState.capabilities : null;
  const activePortalView =
    currentCapabilities === null
      ? null
      : resolveActivePortalView(
          currentCapabilities.capabilities,
          locationSearch,
        );
  const activeInventoryView =
    currentCapabilities === null || activePortalView !== "inventory"
      ? null
      : resolveActiveInventoryView(
          currentCapabilities.capabilities,
          locationSearch,
        );
  const selectedGroupId =
    activePortalView === "groups"
      ? new URLSearchParams(locationSearch).get("group_id")
      : null;
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
          csrf: null,
        });
        fetchCapabilities()
          .then((capabilities) => {
            if (mounted) {
              setAuthState({
                type: "authenticated",
                subject: session.subject,
                capabilities,
                csrf: null,
              });
            }
          })
          .catch(() => {
            if (mounted) {
              setAuthState({
                type: "error",
                message: CAPABILITIES_UNAVAILABLE_MESSAGE,
              });
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
    if (
      currentCapabilities === null ||
      activePortalView !== "inventory" ||
      activeInventoryView === null
    ) {
      setInventoryState({ type: "idle" });
      return;
    }

    let mounted = true;
    const abortController = new AbortController();
    const params = new URLSearchParams(locationSearch);
    setInventoryState({ type: "loading", view: activeInventoryView });

    if (activeInventoryView === "instances") {
      fetchInstances(params, abortController.signal)
        .then((page) => {
          if (mounted) {
            setInventoryState({ type: "ready", view: "instances", page });
          }
        })
        .catch((error: unknown) => {
          if (mounted && !isAbortError(error)) {
            setInventoryState({
              type: "error",
              view: "instances",
              message: "Список ВМ недоступен",
            });
          }
        });
    } else {
      fetchHypervisors(params, abortController.signal)
        .then((page) => {
          if (mounted) {
            setInventoryState({ type: "ready", view: "hypervisors", page });
          }
        })
        .catch((error: unknown) => {
          if (mounted && !isAbortError(error)) {
            setInventoryState({
              type: "error",
              view: "hypervisors",
              message: "Список гипервизоров недоступен",
            });
          }
        });
    }

    return () => {
      mounted = false;
      abortController.abort();
    };
  }, [
    activeInventoryView,
    activePortalView,
    capabilitySignature,
    currentCapabilities,
    locationSearch,
  ]);

  useEffect(() => {
    if (
      currentCapabilities === null ||
      activePortalView !== "inventory" ||
      !hasInventoryAccess(currentCapabilities.capabilities)
    ) {
      setInventoryModulesState({ type: "idle" });
      return;
    }

    let mounted = true;
    setInventoryModulesState({ type: "loading" });
    fetchInventoryModules()
      .then((modules) => {
        if (mounted) {
          setInventoryModulesState({ type: "ready", modules });
        }
      })
      .catch(() => {
        if (mounted) {
          setInventoryModulesState({
            type: "error",
            message: INVENTORY_MODULES_UNAVAILABLE_MESSAGE,
          });
        }
      });

    return () => {
      mounted = false;
    };
  }, [activePortalView, capabilitySignature, currentCapabilities]);

  useEffect(() => {
    if (
      currentCapabilities === null ||
      activePortalView !== "groups" ||
      !hasGroupsAccess(currentCapabilities.capabilities)
    ) {
      setGroupState({ type: "idle" });
      return;
    }

    let mounted = true;
    setGroupState({ type: "loading" });
    fetchGroups()
      .then((response) => {
        if (mounted) {
          setGroupState({ type: "ready", groups: response.items });
        }
      })
      .catch(() => {
        if (mounted) {
          setGroupState({ type: "error", message: "Список групп недоступен" });
        }
      });

    return () => {
      mounted = false;
    };
  }, [activePortalView, capabilitySignature, currentCapabilities]);

  useEffect(() => {
    if (
      currentCapabilities === null ||
      activePortalView !== "groups" ||
      selectedGroupId === null ||
      !hasGroupsAccess(currentCapabilities.capabilities)
    ) {
      setGroupDetailState({ type: "idle" });
      return;
    }

    let mounted = true;
    setGroupDetailState({ type: "loading", groupId: selectedGroupId });
    Promise.all([
      fetchGroup(selectedGroupId),
      fetchGroupMembers(selectedGroupId),
    ])
      .then(([group, membersResponse]) => {
        if (mounted) {
          setGroupDetailState({
            type: "ready",
            group,
            members: membersResponse.items,
          });
        }
      })
      .catch(() => {
        if (mounted) {
          setGroupDetailState({
            type: "error",
            groupId: selectedGroupId,
            message: "Группа недоступна",
          });
        }
      });

    return () => {
      mounted = false;
    };
  }, [
    activePortalView,
    capabilitySignature,
    currentCapabilities,
    selectedGroupId,
  ]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const loginResult = await login(loginName, credential);
      const capabilities = await fetchCapabilities();
      setAuthState({
        type: "authenticated",
        subject: loginResult.subject,
        capabilities,
        csrf: loginResult.csrf,
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
    window.history.pushState(
      {},
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
    setLocationSearch(window.location.search);
  }

  function handleInventoryNextPage(cursor: string) {
    const params = new URLSearchParams(locationSearch);
    params.set("cursor", cursor);
    window.history.pushState(
      {},
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
    setLocationSearch(window.location.search);
  }

  function handleInventoryLinkSelect(href: string) {
    window.history.pushState({}, "", `${window.location.pathname}${href}`);
    setLocationSearch(window.location.search);
  }

  function handleGroupViewSelect() {
    const params = new URLSearchParams(locationSearch);
    params.set("view", "groups");
    params.delete("cursor");
    window.history.pushState(
      {},
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
    setLocationSearch(window.location.search);
  }

  function handleGroupSelect(groupId: string) {
    const params = new URLSearchParams(locationSearch);
    params.set("view", "groups");
    params.set("group_id", groupId);
    params.delete("cursor");
    window.history.pushState(
      {},
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
    setLocationSearch(window.location.search);
  }

  function handleGroupInventoryOpen(group: ResourceGroup) {
    const view = group.resource_type === "host" ? "hypervisors" : "instances";
    const params = new URLSearchParams(locationSearch);
    params.set("view", view);
    params.set("group_id", group.group_id);
    params.delete("cursor");
    params.delete("sort");
    params.delete("columns");
    for (const key of INVENTORY_FILTER_KEYS) {
      params.delete(key);
    }
    window.history.pushState(
      {},
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
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
                    <form
                      className="cloud-ui-login-form"
                      onSubmit={handleLogin}
                    >
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
                          onChange={(event) =>
                            setCredential(event.target.value)
                          }
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
                      <Alert
                        variant="success"
                        title={authState.subject.display_name}
                      />
                      {authState.capabilities === null ? (
                        <Bullseye className="cloud-ui-compact-loading">
                          <Spinner aria-label="Загрузка прав" size="md" />
                        </Bullseye>
                      ) : (
                        hasSessionNavigation(authState.capabilities) && (
                          <nav
                            aria-label="Разделы портала"
                            className="cloud-ui-nav"
                          >
                            {authState.capabilities.capabilities.includes(
                              "group.read",
                            ) && (
                              <a
                                aria-current={
                                  activePortalView === "groups"
                                    ? "page"
                                    : undefined
                                }
                                className="cloud-ui-nav-item"
                                href={groupViewHref(locationSearch)}
                                onClick={(event) => {
                                  event.preventDefault();
                                  handleGroupViewSelect();
                                }}
                              >
                                Группы
                              </a>
                            )}
                            {authState.capabilities.capabilities.includes(
                              "operation.read",
                            ) && (
                              <span className="cloud-ui-nav-item">
                                Операции
                              </span>
                            )}
                            {authState.capabilities.capabilities.includes(
                              "role.manage",
                            ) && (
                              <span className="cloud-ui-nav-item">
                                Управление ролями
                              </span>
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

                  {state.type === "error" && (
                    <Alert variant="danger" title={state.message} />
                  )}

                  {state.type === "ready" && (
                    <div className="cloud-ui-status-content">
                      <Alert
                        variant={
                          state.readiness.status === "ok"
                            ? "success"
                            : "warning"
                        }
                        title={`Готовность API: ${state.readiness.status}`}
                      />

                      <dl
                        className="cloud-ui-dependencies"
                        aria-label="Зависимости сервиса"
                      >
                        {Object.entries(state.readiness.dependencies).map(
                          ([name, dependency]) => (
                            <div className="cloud-ui-dependency-row" key={name}>
                              <dt>{name}</dt>
                              <dd>
                                {dependency.status} - {dependency.detail}
                              </dd>
                            </div>
                          ),
                        )}
                      </dl>
                    </div>
                  )}
                </CardBody>
              </Card>
            </div>
          </div>

          {authState.type === "authenticated" &&
            activePortalView === "groups" && (
              <GroupsWorkArea
                capabilities={authState.capabilities}
                detailState={groupDetailState}
                locationSearch={locationSearch}
                onGroupInventoryOpen={handleGroupInventoryOpen}
                onGroupSelect={handleGroupSelect}
                state={groupState}
              />
            )}

          {authState.type === "authenticated" &&
            activePortalView !== "groups" && (
              <InventoryWorkArea
                activeView={activeInventoryView}
                capabilities={authState.capabilities}
                locationSearch={locationSearch}
                modulesState={inventoryModulesState}
                onInventoryLinkSelect={handleInventoryLinkSelect}
                onInventoryNextPage={handleInventoryNextPage}
                onInventoryViewSelect={handleInventoryViewSelect}
                state={inventoryState}
              />
            )}
        </div>
      </PageSection>
    </Page>
  );
}

function resolveActivePortalView(
  capabilities: string[],
  locationSearch: string,
): PortalView | null {
  const requestedView = new URLSearchParams(locationSearch).get("view");
  const canReadGroups = hasGroupsAccess(capabilities);

  if (requestedView === "groups" && canReadGroups) {
    return "groups";
  }
  if (
    (requestedView === "instances" || requestedView === "hypervisors") &&
    hasInventoryAccess(capabilities)
  ) {
    return "inventory";
  }
  if (hasInventoryAccess(capabilities)) {
    return "inventory";
  }
  if (canReadGroups) {
    return "groups";
  }
  return null;
}

function resolveActiveInventoryView(
  capabilities: string[],
  locationSearch: string,
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

function inventoryViewHref(
  view: InventoryView,
  locationSearch: string,
): string {
  const params = new URLSearchParams(locationSearch);
  params.set("view", view);
  params.delete("cursor");
  return `?${params.toString()}`;
}

function groupViewHref(locationSearch: string): string {
  const params = new URLSearchParams(locationSearch);
  params.set("view", "groups");
  params.delete("cursor");
  return `?${params.toString()}`;
}

function hasSessionNavigation(capabilities: Capabilities): boolean {
  return (
    capabilities.capabilities.includes("group.read") ||
    capabilities.capabilities.includes("operation.read") ||
    capabilities.capabilities.includes("role.manage")
  );
}

function hasGroupsAccess(capabilities: string[]): boolean {
  return capabilities.includes("group.read");
}

function hasInventoryAccess(capabilities: string[]): boolean {
  return (
    capabilities.includes("instance.read") ||
    capabilities.includes("hypervisor.read")
  );
}

function InventoryWorkArea({
  activeView,
  capabilities,
  locationSearch,
  modulesState,
  onInventoryLinkSelect,
  onInventoryNextPage,
  onInventoryViewSelect,
  state,
}: {
  activeView: InventoryView | null;
  capabilities: Capabilities | null;
  locationSearch: string;
  modulesState: InventoryModulesState;
  onInventoryLinkSelect: (href: string) => void;
  onInventoryNextPage: (cursor: string) => void;
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
          {activeView === "instances"
            ? "Виртуальные машины"
            : "Список гипервизоров"}
        </Title>
      </div>
      <InventoryModules state={modulesState} />

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
        renderInstancesPage(
          state.page,
          locationSearch,
          capabilities,
          onInventoryLinkSelect,
          onInventoryNextPage,
        )}

      {state.type === "ready" &&
        state.view === "hypervisors" &&
        activeView === "hypervisors" &&
        renderHypervisorsPage(
          state.page,
          locationSearch,
          capabilities,
          onInventoryLinkSelect,
          onInventoryNextPage,
        )}
    </section>
  );
}

function InventoryNavigation({
  activeView,
  capabilities,
  locationSearch,
  onInventoryViewSelect,
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

function InventoryModules({ state }: { state: InventoryModulesState }) {
  if (state.type === "idle") {
    return null;
  }

  if (state.type === "loading") {
    return (
      <div className="cloud-ui-module-strip" aria-label="Модули inventory">
        <span className="cloud-ui-muted">Загрузка модулей inventory...</span>
      </div>
    );
  }

  if (state.type === "error") {
    return <Alert variant="warning" title={state.message} />;
  }

  return (
    <ul className="cloud-ui-module-strip" aria-label="Модули inventory">
      {state.modules.map((module) => (
        <li className="cloud-ui-module-item" key={module.key}>
          <span>{module.title}</span>
          <span
            className={
              module.enabled
                ? "cloud-ui-badge cloud-ui-badge-enabled"
                : "cloud-ui-badge cloud-ui-badge-disabled"
            }
          >
            {module.enabled ? "Доступно" : "Отключено"}
          </span>
          {module.required_capability !== null && (
            <span className="cloud-ui-module-meta">
              {module.required_capability}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

function GroupsWorkArea({
  capabilities,
  detailState,
  locationSearch,
  onGroupInventoryOpen,
  onGroupSelect,
  state,
}: {
  capabilities: Capabilities | null;
  detailState: GroupDetailState;
  locationSearch: string;
  onGroupInventoryOpen: (group: ResourceGroup) => void;
  onGroupSelect: (groupId: string) => void;
  state: GroupState;
}) {
  if (capabilities === null) {
    return (
      <section aria-label="Группы" className="cloud-ui-workarea">
        <Bullseye className="cloud-ui-loading">
          <Spinner aria-label="Загрузка прав групп" />
        </Bullseye>
      </section>
    );
  }

  return (
    <section aria-label="Группы" className="cloud-ui-workarea">
      <div className="cloud-ui-workarea-header">
        <Title headingLevel="h2" size="lg">
          Группы
        </Title>
      </div>

      {state.type === "loading" && (
        <Bullseye className="cloud-ui-loading">
          <Spinner aria-label="Загрузка групп" />
        </Bullseye>
      )}

      {state.type === "error" && (
        <Alert variant="danger" title={state.message} />
      )}

      {state.type === "ready" &&
        (state.groups.length === 0 ? (
          <p className="cloud-ui-empty">Группы не найдены.</p>
        ) : (
          <div className="cloud-ui-table-wrapper">
            <table
              className="cloud-ui-table cloud-ui-group-table"
              aria-label="Таблица групп"
            >
              <thead>
                <tr>
                  <th scope="col">Имя</th>
                  <th scope="col">Тип</th>
                  <th scope="col">Режим</th>
                  <th scope="col">Область</th>
                  <th scope="col">Ревизия</th>
                </tr>
              </thead>
              <tbody>
                {state.groups.map((group) => (
                  <tr key={group.group_id}>
                    <th scope="row">
                      <button
                        className="cloud-ui-link-button"
                        onClick={() => onGroupSelect(group.group_id)}
                        type="button"
                      >
                        {group.name}
                      </button>
                    </th>
                    <td>{formatGroupResourceType(group.resource_type)}</td>
                    <td>{formatGroupMembershipMode(group.membership_mode)}</td>
                    <td>{formatGroupScope(group)}</td>
                    <td>{group.revision}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      {detailState.type === "loading" && (
        <Bullseye className="cloud-ui-loading">
          <Spinner aria-label="Загрузка деталей группы" />
        </Bullseye>
      )}

      {detailState.type === "error" && (
        <Alert variant="danger" title={detailState.message} />
      )}

      {detailState.type === "ready" && (
        <GroupDetailPanel
          capabilities={capabilities}
          group={detailState.group}
          locationSearch={locationSearch}
          members={detailState.members}
          onGroupInventoryOpen={onGroupInventoryOpen}
        />
      )}
    </section>
  );
}

function GroupDetailPanel({
  capabilities,
  group,
  locationSearch,
  members,
  onGroupInventoryOpen,
}: {
  capabilities: Capabilities;
  group: ResourceGroup;
  locationSearch: string;
  members: GroupMember[];
  onGroupInventoryOpen: (group: ResourceGroup) => void;
}) {
  const capabilitySet = capabilities.capabilities;
  const canManageGroups = capabilitySet.includes("group.manage");
  const canSearchMembers =
    canManageGroups &&
    group.membership_mode !== "dynamic" &&
    ((group.resource_type === "vm" &&
      capabilitySet.includes("instance.read")) ||
      (group.resource_type === "host" &&
        capabilitySet.includes("hypervisor.read")));
  const canOpenInventory =
    (group.resource_type === "vm" && capabilitySet.includes("instance.read")) ||
    (group.resource_type === "host" &&
      capabilitySet.includes("hypervisor.read"));
  const canPreview =
    group.membership_mode === "dynamic" &&
    ((group.resource_type === "vm" &&
      capabilitySet.includes("instance.read")) ||
      (group.resource_type === "host" &&
        capabilitySet.includes("hypervisor.read")));

  return (
    <section aria-label="Детали группы" className="cloud-ui-group-detail">
      <div className="cloud-ui-group-detail-header">
        <Title headingLevel="h3" size="md">
          {group.name}
        </Title>
        {canOpenInventory && (
          <a
            className="cloud-ui-action-link"
            href={groupInventoryHref(group, locationSearch)}
            onClick={(event) => {
              event.preventDefault();
              onGroupInventoryOpen(group);
            }}
          >
            Открыть в инвентаре
          </a>
        )}
      </div>

      <dl className="cloud-ui-detail-list">
        <div>
          <dt>Владелец</dt>
          <dd>{group.owner_subject_id}</dd>
        </div>
        <div>
          <dt>Область</dt>
          <dd>{formatGroupScope(group)}</dd>
        </div>
        <div>
          <dt>Ревизия</dt>
          <dd>{group.revision}</dd>
        </div>
        <div>
          <dt>Тип</dt>
          <dd>{formatGroupResourceType(group.resource_type)}</dd>
        </div>
        <div>
          <dt>Режим</dt>
          <dd>{formatGroupMembershipMode(group.membership_mode)}</dd>
        </div>
      </dl>

      <section aria-label="Участники группы" className="cloud-ui-group-panel">
        <Title headingLevel="h4" size="md">
          Участники
        </Title>
        {members.length === 0 ? (
          <p className="cloud-ui-empty">Участники не назначены.</p>
        ) : (
          <ul className="cloud-ui-resource-list">
            {members.map((member) => (
              <li
                key={`${member.resource_type}:${member.cloud_id}:${member.region_id}:${member.resource_id}`}
              >
                <span>{member.resource_id}</span>
                <span className="cloud-ui-muted">
                  {member.cloud_id}/{member.region_id}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {canSearchMembers && <MemberSearchPanel group={group} />}
      {canPreview && <GroupPreviewPanel group={group} />}
    </section>
  );
}

function MemberSearchPanel({ group }: { group: ResourceGroup }) {
  const [query, setQuery] = useState("");
  const [searchState, setSearchState] = useState<MemberSearchState>({
    type: "idle",
  });

  useEffect(() => {
    setQuery("");
    setSearchState({ type: "idle" });
  }, [group.group_id]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams();
    const trimmedQuery = query.trim();
    if (trimmedQuery !== "") {
      params.set("q", trimmedQuery);
    }

    setSearchState({ type: "loading" });
    try {
      if (group.resource_type === "vm") {
        const page = await fetchInstances(params);
        setSearchState({ type: "instances", page });
        return;
      }
      if (group.resource_type === "host") {
        const page = await fetchHypervisors(params);
        setSearchState({ type: "hypervisors", page });
        return;
      }
      setSearchState({
        type: "error",
        message: "Поиск mixed групп недоступен",
      });
    } catch {
      setSearchState({ type: "error", message: "Поиск ресурсов недоступен" });
    }
  }

  return (
    <section aria-label="Подбор участников" className="cloud-ui-group-panel">
      <Title headingLevel="h4" size="md">
        Подбор участников
      </Title>
      <form className="cloud-ui-inline-form" onSubmit={handleSearch}>
        <label>
          <span>Поиск ресурсов</span>
          <input
            onChange={(event) => setQuery(event.target.value)}
            type="search"
            value={query}
          />
        </label>
        <Button type="submit" variant="secondary">
          {group.resource_type === "host" ? "Найти хосты" : "Найти ВМ"}
        </Button>
      </form>

      {searchState.type === "loading" && (
        <Bullseye className="cloud-ui-compact-loading">
          <Spinner aria-label="Поиск ресурсов" size="md" />
        </Bullseye>
      )}
      {searchState.type === "error" && (
        <Alert variant="warning" title={searchState.message} />
      )}
      {searchState.type === "instances" &&
        renderMemberSearchInstances(searchState.page)}
      {searchState.type === "hypervisors" &&
        renderMemberSearchHypervisors(searchState.page)}
    </section>
  );
}

function GroupPreviewPanel({ group }: { group: ResourceGroup }) {
  const [ruleText, setRuleText] = useState(() => formatGroupRule(group));
  const [previewState, setPreviewState] = useState<PreviewState>({
    type: "idle",
  });

  useEffect(() => {
    setRuleText(formatGroupRule(group));
    setPreviewState({ type: "idle" });
  }, [group]);

  async function handlePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const rule = parseGroupRule(ruleText);
    if (rule === null) {
      setPreviewState({ type: "error", message: "Правило группы отклонено" });
      return;
    }

    setPreviewState({ type: "loading" });
    try {
      const response = await previewGroupRule(group.group_id, rule);
      setPreviewState({ type: "ready", response });
    } catch (error: unknown) {
      setPreviewState({
        type: "error",
        message:
          error instanceof Error ? error.message : "Правило группы отклонено",
      });
    }
  }

  return (
    <section aria-label="Preview группы" className="cloud-ui-group-panel">
      <Title headingLevel="h4" size="md">
        Preview
      </Title>
      <form className="cloud-ui-rule-form" onSubmit={handlePreview}>
        <label>
          <span>Правило preview</span>
          <textarea
            onChange={(event) => setRuleText(event.target.value)}
            rows={5}
            value={ruleText}
          />
        </label>
        <Button type="submit" variant="secondary">
          Предпросмотр
        </Button>
      </form>

      {previewState.type === "loading" && (
        <Bullseye className="cloud-ui-compact-loading">
          <Spinner aria-label="Загрузка preview" size="md" />
        </Bullseye>
      )}
      {previewState.type === "error" && (
        <Alert variant="warning" title={previewState.message} />
      )}
      {previewState.type === "ready" &&
        renderGroupPreview(previewState.response)}
    </section>
  );
}

function renderMemberSearchInstances(page: InventoryPage<InstanceItem>) {
  if (page.items.length === 0) {
    return <p className="cloud-ui-empty">Ресурсы не найдены.</p>;
  }
  return (
    <ul className="cloud-ui-resource-list" aria-label="Найденные ресурсы">
      {page.items.map((item) => (
        <li key={`${item.cloud_id}:${item.region_id}:${item.instance_id}`}>
          <span>{item.name}</span>
          <span className="cloud-ui-muted">
            {item.cloud_id}/{item.region_id}
          </span>
        </li>
      ))}
    </ul>
  );
}

function renderMemberSearchHypervisors(page: InventoryPage<HypervisorItem>) {
  if (page.items.length === 0) {
    return <p className="cloud-ui-empty">Ресурсы не найдены.</p>;
  }
  return (
    <ul className="cloud-ui-resource-list" aria-label="Найденные ресурсы">
      {page.items.map((item) => (
        <li key={`${item.cloud_id}:${item.region_id}:${item.hypervisor_id}`}>
          <span>{item.host_name}</span>
          <span className="cloud-ui-muted">
            {item.cloud_id}/{item.region_id}
          </span>
        </li>
      ))}
    </ul>
  );
}

function renderGroupPreview(response: GroupPreviewResponse) {
  return (
    <div className="cloud-ui-preview-result">
      <div
        className="cloud-ui-inventory-notices"
        aria-label="Результат preview"
      >
        <span className="cloud-ui-badge">
          Оценка: {response.count_estimate}
        </span>
        <span className="cloud-ui-badge">Ограничение: {response.limit}</span>
        {response.warnings.map((warning) => (
          <span className="cloud-ui-warning-text" key={warning}>
            {warning}
          </span>
        ))}
        {response.explain.map((line) => (
          <span className="cloud-ui-badge" key={line}>
            {line}
          </span>
        ))}
      </div>
      {response.items.length === 0 ? (
        <p className="cloud-ui-empty">Preview пуст.</p>
      ) : (
        <ul className="cloud-ui-resource-list" aria-label="Preview ресурсов">
          {response.items.map((item) => (
            <li key={previewItemKey(item)}>
              <span>{previewItemLabel(item)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function renderInventoryNotices<T>(page: InventoryPage<T>) {
  return (
    <div className="cloud-ui-inventory-notices" aria-label="Состояние данных">
      {page.partial && (
        <span className="cloud-ui-badge cloud-ui-badge-warning">
          Частичные данные
        </span>
      )}
      {page.freshness?.is_stale && (
        <span className="cloud-ui-badge cloud-ui-badge-stale">
          Данные устарели
        </span>
      )}
      {page.freshness?.observed_at && (
        <span className="cloud-ui-badge">
          Наблюдение: {formatUtc(page.freshness.observed_at)}
        </span>
      )}
      {page.warnings.map((warning) => (
        <span
          className="cloud-ui-warning-text"
          key={`${warning.source}:${warning.code}`}
        >
          {warning.detail}
        </span>
      ))}
    </div>
  );
}

function renderInstancesPage(
  page: InventoryPage<InstanceItem>,
  locationSearch: string,
  capabilities: Capabilities,
  onInventoryLinkSelect: (href: string) => void,
  onInventoryNextPage: (cursor: string) => void,
) {
  const columns = parseInstanceColumns(locationSearch);
  const density = parseDensity(locationSearch);
  const canReadHypervisors =
    capabilities.capabilities.includes("hypervisor.read");
  const canRefreshInstances =
    capabilities.capabilities.includes("instance.refresh");

  return (
    <div className="cloud-ui-inventory-page">
      {renderInventoryNotices(page)}
      {page.items.length === 0 ? (
        <p className="cloud-ui-empty">Нет ВМ для выбранных фильтров.</p>
      ) : (
        <div className="cloud-ui-table-wrapper">
          <table
            className="cloud-ui-table"
            aria-label="Таблица ВМ"
            data-density={density}
          >
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} scope="col">
                    {INSTANCE_COLUMN_LABELS[column]}
                  </th>
                ))}
                {canRefreshInstances && <th scope="col">Действия</th>}
              </tr>
            </thead>
            <tbody>
              {page.items.map((item) => (
                <tr
                  key={`${item.cloud_id}:${item.region_id}:${item.instance_id}`}
                >
                  {columns.map((column) =>
                    renderInstanceCell(
                      column,
                      item,
                      canReadHypervisors,
                      locationSearch,
                      onInventoryLinkSelect,
                    ),
                  )}
                  {canRefreshInstances && (
                    <td>
                      <Button
                        aria-label={`Обновить ${item.name}`}
                        className="cloud-ui-table-action"
                        isDisabled
                        type="button"
                        variant="secondary"
                      >
                        Обновить
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {page.next_cursor !== null && (
        <div className="cloud-ui-pagination">
          <Button
            onClick={() => onInventoryNextPage(page.next_cursor as string)}
            type="button"
            variant="secondary"
          >
            Следующая страница
          </Button>
        </div>
      )}
    </div>
  );
}

function renderHypervisorsPage(
  page: InventoryPage<HypervisorItem>,
  locationSearch: string,
  capabilities: Capabilities,
  onInventoryLinkSelect: (href: string) => void,
  onInventoryNextPage: (cursor: string) => void,
) {
  const columns = parseHypervisorColumns(locationSearch);
  const density = parseDensity(locationSearch);
  const canReadInstances = capabilities.capabilities.includes("instance.read");

  return (
    <div className="cloud-ui-inventory-page">
      {renderInventoryNotices(page)}
      {page.items.length === 0 ? (
        <p className="cloud-ui-empty">
          Нет гипервизоров для выбранных фильтров.
        </p>
      ) : (
        <div className="cloud-ui-table-wrapper">
          <table
            className="cloud-ui-table"
            aria-label="Таблица гипервизоров"
            data-density={density}
          >
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} scope="col">
                    {HYPERVISOR_COLUMN_LABELS[column]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {page.items.map((item) => (
                <tr
                  key={`${item.cloud_id}:${item.region_id}:${item.hypervisor_id}`}
                >
                  {columns.map((column) =>
                    renderHypervisorCell(
                      column,
                      item,
                      canReadInstances,
                      locationSearch,
                      onInventoryLinkSelect,
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {page.next_cursor !== null && (
        <div className="cloud-ui-pagination">
          <Button
            onClick={() => onInventoryNextPage(page.next_cursor as string)}
            type="button"
            variant="secondary"
          >
            Следующая страница
          </Button>
        </div>
      )}
    </div>
  );
}

function renderInstanceCell(
  column: InstanceColumnKey,
  item: InstanceItem,
  canReadHypervisors: boolean,
  locationSearch: string,
  onInventoryLinkSelect: (href: string) => void,
) {
  const key = `${item.instance_id}:${column}`;
  if (column === "name") {
    return (
      <th key={key} scope="row">
        {item.name}
      </th>
    );
  }
  if (column === "host_name") {
    return (
      <td key={key}>
        {item.host_name !== null && canReadHypervisors
          ? renderInventoryLink(
              item.host_name,
              filteredInventoryHref(
                "hypervisors",
                { host_name: item.host_name },
                locationSearch,
              ),
              onInventoryLinkSelect,
            )
          : formatNullable(item.host_name)}
      </td>
    );
  }
  if (column === "hypervisor_id") {
    return (
      <td key={key}>
        {item.hypervisor_id !== null && canReadHypervisors
          ? renderInventoryLink(
              item.hypervisor_id,
              filteredInventoryHref(
                "hypervisors",
                { q: item.hypervisor_id },
                locationSearch,
              ),
              onInventoryLinkSelect,
            )
          : formatNullable(item.hypervisor_id)}
      </td>
    );
  }
  if (column === "observed_at") {
    return <td key={key}>{formatUtc(item.observed_at)}</td>;
  }
  return <td key={key}>{formatInstanceValue(column, item)}</td>;
}

function renderHypervisorCell(
  column: HypervisorColumnKey,
  item: HypervisorItem,
  canReadInstances: boolean,
  locationSearch: string,
  onInventoryLinkSelect: (href: string) => void,
) {
  const key = `${item.hypervisor_id}:${column}`;
  if (column === "host_name") {
    return (
      <th key={key} scope="row">
        {canReadInstances
          ? renderInventoryLink(
              item.host_name,
              filteredInventoryHref(
                "instances",
                { host_name: item.host_name },
                locationSearch,
              ),
              onInventoryLinkSelect,
            )
          : item.host_name}
      </th>
    );
  }
  if (column === "running_vms") {
    const label = `${item.running_vms} ВМ`;
    return (
      <td key={key}>
        {canReadInstances
          ? renderInventoryLink(
              label,
              filteredInventoryHref(
                "instances",
                { host_name: item.host_name },
                locationSearch,
              ),
              onInventoryLinkSelect,
            )
          : label}
      </td>
    );
  }
  if (column === "capacity") {
    return (
      <td key={key}>
        vCPU {item.vcpus_used}/{item.vcpus_total}; RAM{" "}
        {formatRam(item.ram_mb_used)} / {formatRam(item.ram_mb_total)}
      </td>
    );
  }
  if (column === "observed_at") {
    return <td key={key}>{formatUtc(item.observed_at)}</td>;
  }
  return <td key={key}>{formatHypervisorValue(column, item)}</td>;
}

function renderInventoryLink(
  label: string,
  href: string,
  onInventoryLinkSelect: (href: string) => void,
) {
  return (
    <a
      href={href}
      onClick={(event) => {
        event.preventDefault();
        onInventoryLinkSelect(href);
      }}
    >
      {label}
    </a>
  );
}

function filteredInventoryHref(
  view: InventoryView,
  filters: Partial<Record<(typeof INVENTORY_FILTER_KEYS)[number], string>>,
  locationSearch: string,
): string {
  const params = new URLSearchParams(locationSearch);
  params.set("view", view);
  params.delete("cursor");
  params.delete("sort");
  params.delete("columns");
  for (const key of INVENTORY_FILTER_KEYS) {
    params.delete(key);
  }
  for (const [key, value] of Object.entries(filters)) {
    params.set(key, value);
  }
  return `?${params.toString()}`;
}

function parseDensity(locationSearch: string): Density {
  const density = new URLSearchParams(locationSearch).get("density");
  return density === "compact" ? "compact" : "comfortable";
}

function parseInstanceColumns(locationSearch: string): InstanceColumnKey[] {
  const requestedColumns =
    parseColumnList(locationSearch).filter(isInstanceColumnKey);
  return requestedColumns.length > 0
    ? requestedColumns
    : DEFAULT_INSTANCE_COLUMNS;
}

function parseHypervisorColumns(locationSearch: string): HypervisorColumnKey[] {
  const requestedColumns = parseColumnList(locationSearch).filter(
    isHypervisorColumnKey,
  );
  return requestedColumns.length > 0
    ? requestedColumns
    : DEFAULT_HYPERVISOR_COLUMNS;
}

function parseColumnList(locationSearch: string): string[] {
  const rawColumns = new URLSearchParams(locationSearch).get("columns");
  if (rawColumns === null) {
    return [];
  }
  return rawColumns
    .split(",")
    .map((column) => column.trim())
    .filter((column) => column !== "");
}

function isInstanceColumnKey(value: string): value is InstanceColumnKey {
  return (INSTANCE_COLUMN_KEYS as readonly string[]).includes(value);
}

function isHypervisorColumnKey(value: string): value is HypervisorColumnKey {
  return (HYPERVISOR_COLUMN_KEYS as readonly string[]).includes(value);
}

function formatInstanceValue(
  column: InstanceColumnKey,
  item: InstanceItem,
): string {
  if (column === "status") {
    return item.status;
  }
  if (column === "project_id") {
    return item.project_id;
  }
  if (column === "availability_zone") {
    return formatNullable(item.availability_zone);
  }
  return "";
}

function formatHypervisorValue(
  column: HypervisorColumnKey,
  item: HypervisorItem,
): string {
  if (column === "service_status") {
    return item.service_status;
  }
  if (column === "service_state") {
    return item.service_state;
  }
  if (column === "availability_zone") {
    return formatNullable(item.availability_zone);
  }
  return "";
}

function formatNullable(value: string | null): string {
  return value ?? "-";
}

function formatGroupScope(group: ResourceGroup): string {
  return `${group.scope.type}:${group.scope.id ?? "all"}`;
}

function formatGroupResourceType(
  resourceType: ResourceGroup["resource_type"],
): string {
  if (resourceType === "vm") {
    return "ВМ";
  }
  if (resourceType === "host") {
    return "Хосты";
  }
  return "Смешанная";
}

function formatGroupMembershipMode(
  mode: ResourceGroup["membership_mode"],
): string {
  if (mode === "explicit") {
    return "Явная";
  }
  if (mode === "dynamic") {
    return "Динамическая";
  }
  return "Импорт";
}

function groupInventoryHref(
  group: ResourceGroup,
  locationSearch: string,
): string {
  const params = new URLSearchParams(locationSearch);
  params.set(
    "view",
    group.resource_type === "host" ? "hypervisors" : "instances",
  );
  params.set("group_id", group.group_id);
  params.delete("cursor");
  params.delete("sort");
  params.delete("columns");
  for (const key of INVENTORY_FILTER_KEYS) {
    params.delete(key);
  }
  return `?${params.toString()}`;
}

function formatGroupRule(group: ResourceGroup): string {
  const rule =
    group.rule_body_json ??
    (group.resource_type === "host"
      ? { field: "service_status", operator: "eq", value: "enabled" }
      : { field: "status", operator: "eq", value: "ACTIVE" });
  return JSON.stringify(rule, null, 2);
}

function parseGroupRule(value: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(value);
    return isPlainObject(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function previewItemKey(item: Record<string, unknown>): string {
  for (const key of [
    "instance_id",
    "hypervisor_id",
    "resource_id",
    "name",
    "host_name",
  ]) {
    const value = item[key];
    if (typeof value === "string" && value !== "") {
      return `${key}:${value}`;
    }
  }
  return JSON.stringify(item);
}

function previewItemLabel(item: Record<string, unknown>): string {
  for (const key of [
    "name",
    "host_name",
    "instance_id",
    "hypervisor_id",
    "resource_id",
  ]) {
    const value = item[key];
    if (typeof value === "string" && value !== "") {
      return value;
    }
  }
  return "resource";
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
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
