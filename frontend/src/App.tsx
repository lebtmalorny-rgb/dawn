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
  type Readiness,
  type Subject,
  fetchCapabilities,
  fetchCurrentSession,
  fetchReadiness,
  login
} from "./api";
import "./styles.css";

const READINESS_UNAVAILABLE_MESSAGE = "Готовность API недоступна";
const SESSION_UNAVAILABLE_MESSAGE = "Сессия недоступна";

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

export function App() {
  const [state, setState] = useState<LoadState>({ type: "loading" });
  const [authState, setAuthState] = useState<AuthState>({ type: "loading" });
  const [loginName, setLoginName] = useState("");
  const [credential, setCredential] = useState("");

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

  return (
    <Page>
      <PageSection className="cloud-ui-page">
        <div className="cloud-ui-layout">
          <Title headingLevel="h1" size="xl">
            Cloud UI
          </Title>

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

              {authState.type === "error" && <Alert variant="danger" title={authState.message} />}

              {authState.type === "authenticated" && (
                <div className="cloud-ui-session">
                  <Alert variant="success" title={authState.subject.display_name} />
                  <nav aria-label="Разделы портала" className="cloud-ui-nav">
                    {authState.capabilities?.capabilities.includes("operation.read") && (
                      <span>Операции</span>
                    )}
                    {authState.capabilities?.capabilities.includes("role.manage") && (
                      <span>Управление ролями</span>
                    )}
                  </nav>
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
                    {Object.entries(state.readiness.dependencies).map(([name, dependency]) => (
                      <div className="cloud-ui-dependency-row" key={name}>
                        <dt>{name}</dt>
                        <dd>
                          {dependency.status} - {dependency.detail}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </PageSection>
    </Page>
  );
}
