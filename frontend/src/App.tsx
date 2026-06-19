import "@patternfly/react-core/dist/styles/base.css";

import {
  Alert,
  Bullseye,
  Card,
  CardBody,
  CardTitle,
  Page,
  PageSection,
  Spinner,
  Title
} from "@patternfly/react-core";
import { useEffect, useState } from "react";

import { type Readiness, fetchReadiness } from "./api";
import "./styles.css";

const READINESS_UNAVAILABLE_MESSAGE = "Готовность API недоступна";

type LoadState =
  | { type: "loading" }
  | { type: "ready"; readiness: Readiness }
  | { type: "error"; message: string };

export function App() {
  const [state, setState] = useState<LoadState>({ type: "loading" });

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

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <Page>
      <PageSection className="cloud-ui-page">
        <div className="cloud-ui-layout">
          <Title headingLevel="h1" size="xl">
            Cloud UI
          </Title>

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
