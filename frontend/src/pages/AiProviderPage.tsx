import { useState } from "react";
import { useAiConnection, useConnectAi, useDisconnectAi } from "../api/queries";
import { ApiError } from "../api/client";

const MODEL_PLACEHOLDER: Record<string, string> = {
  openai: "gpt-4o-mini (default)",
  anthropic: "claude-3-5-sonnet-latest (default)",
  cursor: "leave blank for Cursor's default",
};

const KEY_PLACEHOLDER: Record<string, string> = {
  openai: "sk-…",
  anthropic: "sk-ant-…",
  cursor: "cursor_…",
};

export function AiProviderPage() {
  const connection = useAiConnection();
  const connect = useConnectAi();
  const disconnect = useDisconnectAi();

  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");

  const connected = !!connection.data;

  return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <h1>AI Provider</h1>
      <p className="secondary">
        Connect your own AI provider. Every run you start is reviewed using your key. The key
        is encrypted at rest and never shown again, sent to the browser, or written to logs.
        Until you connect one, runs use the platform default (or the offline mock).
      </p>

      {connected ? (
        <div className="card">
          <div className="row spread">
            <div>
              <div style={{ fontWeight: 600 }}>Connected: {connection.data!.provider}</div>
              <div className="muted" style={{ fontSize: 13 }}>
                model: {connection.data!.model ?? "default"}
              </div>
            </div>
            <div className="row" style={{ gap: 10 }}>
              <span className="pill passed">
                <span className="dot" />
                Connected
              </span>
              <button className="btn" disabled={disconnect.isPending} onClick={() => disconnect.mutate()}>
                Disconnect
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <h3>Connect a provider</h3>
          <div className="field">
            <label htmlFor="provider">Provider</label>
            <select
              id="provider"
              className="select"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="cursor">Cursor</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="key">API key</label>
            <input
              id="key"
              className="input"
              type="password"
              value={apiKey}
              placeholder={KEY_PLACEHOLDER[provider] ?? "key…"}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="model">Model (optional)</label>
            <input
              id="model"
              className="input"
              value={model}
              placeholder={MODEL_PLACEHOLDER[provider]}
              onChange={(e) => setModel(e.target.value)}
            />
          </div>
          {connect.isError && (
            <div className="error" style={{ marginBottom: 10 }}>
              {(connect.error as ApiError).message}
            </div>
          )}
          <button
            className="btn primary"
            disabled={!apiKey || connect.isPending}
            onClick={() => connect.mutate({ provider, api_key: apiKey, model: model || undefined })}
          >
            {connect.isPending ? "Connecting…" : "Connect"}
          </button>
        </div>
      )}
    </div>
  );
}
