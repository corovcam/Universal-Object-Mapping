# UOM Assistant Frontend: UI Component Specifications

This document outlines the design specifications, styling variables, parsing algorithms, and deep-linking integrations of the frontend components in the **UOM Assistant**.

---

## 1. Onboarding & Settings Panel (`ConfigModal`)

*   **File Path**: [`frontend/uom-translator-ui/components/config-modal.tsx`](../../frontend/uom-translator-ui/components/config-modal.tsx)
*   **Component**: `ConfigModal`

The settings panel allows developers to configure LLM providers, database connection strings, and Daytona sandbox timeouts.

### 1.1 Default Configuration Object
When no user configuration is present in the environment variables (server side, so not readable by the client), the application falls back to defaults tuned for local deployment:
```typescript
const DEFAULT_UOM_GRAPH_CONTEXT = {
	ollamaHost: process.env.OLLAMA_HOST || "http://localhost:11434",
	model: process.env.MODEL || "einfra/kimi-k2.6",
	openaiApiUrl: process.env.OPENAI_API_URL || "https://llm.ai.e-infra.cz/v1",
	openaiApiKey: "",
	mssqlConnectionString: process.env.MSSQL_CONNECTION_STRING || "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True",
	mongodbUri: process.env.MONGODB_URI || "mongodb://localhost:27027",
	neo4jUri: process.env.NEO4J_URI || "neo4j://localhost:7697",
	neo4jPassword: process.env.NEO4J_PASSWORD || "password",
	daytonaTimeout: process.env.DAYTONA_TIMEOUT ? parseInt(process.env.DAYTONA_TIMEOUT) : 480,
	dbToolboxUri: process.env.DB_TOOLBOX_URI || "http://localhost:5010",
	daytonaApiUrl: process.env.DAYTONA_API_URL || "http://localhost:3000/api",
	daytonaApiKey: "",
	daytonaTarget: (process.env.DAYTONA_TARGET as "us" | "eu") || "us",
	mongodbMcpUri: process.env.MONGODB_MCP_URI || "http://localhost:3010/mcp",
};
```

### 1.2 Mount & Saving Lifecycle
*   **On Mount**: Checks for the existence of `localStorage.getItem("uom_translator_config")`. If found, it parses the JSON and merges it over the default state object: `setConfig({  ...appContext.defaultUomGraphContext, ...JSON.parse(saved) })`.
*   **On Save**: Encodes variables into the storage keys and sets the onboarding flag to prevent automatic popups on subsequent visits:
    ```typescript
    localStorage.setItem("uom_translator_config", JSON.stringify(config));
    localStorage.setItem("uom_config_onboarded", "true");
    ...
    ```

---

## 2. Daytona Remote IDE Connection Gateway (`IdeLink`)

*   **File Path**: [`frontend/uom-translator-ui/components/ide-link.tsx`](../../frontend/uom-translator-ui/components/ide-link.tsx)
*   **Component**: `IdeLink`

This component lets developers open their local IDE directly inside the Daytona container sandbox running the compiler validation.

### 2.1 API Data Acquisition Flow
Connecting an IDE to an active Daytona sandbox involves the following steps:
1.  **Metadata Inspection**: Fetches container state for the active framework by sending a GET request to `/sandboxes/framework/${activeFramework}`.
2.  **Credential Provisioning**: Dispatches a POST request to `/sandbox/${id}/ssh-token` to provision temporary connection credentials. The API returns the connection command and token:
    ```json
    {
      "ssh_command": "ssh -p 2222 sandbox@localhost",
      "token": "token-string-here"
    }
    ```
3.  **Context Switching**: Triggers platform updates to sync target framework details (.NET vs Java compiler environments).

### 2.2 SSH Connection Command Parser
The component uses a regular expression to parse the raw SSH command and extract the connection details:
```typescript
const parseSshCommand = (cmd?: string, token?: string) => {
    let user = null;
    let host = process.env.NEXT_PUBLIC_SSH_GATEWAY_URL ? new URL(process.env.NEXT_PUBLIC_SSH_GATEWAY_URL).hostname : "localhost";
    let port = process.env.NEXT_PUBLIC_SSH_GATEWAY_URL ? new URL(process.env.NEXT_PUBLIC_SSH_GATEWAY_URL).port : "2222";
    if (!cmd && !token) return { user, host, port };
    const match = cmd?.match(/ssh\s+(?:-p\s+(\d+)\s+)?([^@\s]+)@([^\s]+)/);
    if (match) {
        if (match[1] && match[1] !== "2222") port = match[1];
        port = port !== "2222" ? port : "2222";
        user = match[2];
        host = host !== "localhost" ? host : match[3];
    }
    if (!user) user = token ?? null;
    return { user, host, port };
};
```

### 2.3 Deep-Linking Protocols
The extracted credentials are mapped to deep-link protocols:
*   **VS Code**: `vscode://vscode-remote/ssh-remote+${user}@${host}:${port}/sandbox`
*   **Cursor**: `cursor://vscode-remote/ssh-remote+${user}@${host}:${port}/sandbox`

---

## 3. Auto-Scroll JSON Tree Visualizer (`AutoScrollJsonViewer`)

*   **File Path**: [`frontend/uom-translator-ui/components/json-viewer.tsx`](../../frontend/uom-translator-ui/components/json-viewer.tsx)
*   **Component**: `AutoScrollJsonViewer`

Renders streaming JSON structures (such as validation details or DeepDiff results) using [`@uiw/react-json-view`](https://uiwjs.github.io/react-json-view/).

### 3.1 Pinned Scrolling & MutationObserver
To keep the viewport aligned with streaming content, the component uses a `MutationObserver` combined with a pinning reference to prevent closures from losing scroll state during updates:
```typescript
const [isPinned, setIsPinned] = useState(true);
const isPinnedRef = useRef(isPinned);

// Sync reference with state
useEffect(() => {
    isPinnedRef.current = isPinned;
}, [isPinned]);

// Listen to container mutations
useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new MutationObserver(() => {
        if (isPinnedRef.current) {
            container.scrollTop = container.scrollHeight - container.clientHeight;
        }
    });

    observer.observe(container, {
        childList: true,
        subtree: true,
        characterData: true,
    });

    return () => observer.disconnect();
}, []);
```

### 3.2 Value Change Hook
If new data is received while pinned, the component scrolls the viewport to the bottom:
```typescript
useEffect(() => {
    const container = containerRef.current;
    if (!container || value === undefined) return;
    if (isPinnedRef.current) {
        container.scrollTop = container.scrollHeight - container.clientHeight;
    }
}, [value]);
```

### 3.3 Scroll Threshold Check
If the user scrolls up past a **15px** threshold, auto-scrolling is disabled to allow manual inspection:
```typescript
const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    
    // Toggle pinning off if user scrolls up past the 15px threshold
    const isAtBottom = scrollHeight - clientHeight - scrollTop < 15;
    if (isPinnedRef.current !== isAtBottom) {
        setIsPinned(isAtBottom);
    }
};
```

---

## 4. Markdown & Partial JSON Parsers (`StreamdownText` & `MarkdownText`)

*   **File Paths**: 
    *   [`frontend/uom-translator-ui/components/streamdown-text.tsx`](../../frontend/uom-translator-ui/components/streamdown-text.tsx)
    *   [`frontend/uom-translator-ui/components/assistant-ui/markdown-text.tsx`](../../frontend/uom-translator-ui/components/assistant-ui/markdown-text.tsx)
    *   [`frontend/uom-translator-ui/components/assistant-ui/shiki-highlighter.tsx`](../../frontend/uom-translator-ui/components/assistant-ui/shiki-highlighter.tsx)

These components parse and render streaming markdown text from the assistant via Vercel's [`streamdown`](https://github.com/vercel/streamdown), [`react-markdown`](https://github.com/remarkjs/react-markdown), and[ `react-shiki`](https://react-shiki.vercel.app/) syntax highlighter.

### 4.1 Partial JSON Parsing Algorithm
To display streaming JSON code blocks before they are fully generated, the syntax highlighter uses a partial JSON decoder ([partial-json](https://github.com/promplate/partial-json-parser-js) package) to close open braces and quotes on-the-fly, rendering the result as an interactive tree:
```typescript
import { Allow, parse as parsePartialJson } from "partial-json";

const codeString = String(props.code || "").trim().replace(/^"|"$/g, "");
if (props.language === "json" && codeString.startsWith("{")) {
    try {
        // Parse partial JSON objects on-the-fly
        const parsed = parsePartialJson(codeString, Allow.ALL);
        return <AutoScrollJsonViewer value={parsed} />;
    } catch {
        // Fall back to default raw text rendering if parsing fails
    }
}
```

### 4.2 Shiki Syntax Highlighter
Non-JSON blocks are styled using `react-shiki` with dual theme support (`github-light` and `github-dark` presets), matching the user's active theme.

---

## 5. Reasoning drawers (`Reasoning`)

*   **File Path**: [`frontend/uom-translator-ui/components/assistant-ui/reasoning.tsx`](../../frontend/uom-translator-ui/components/assistant-ui/reasoning.tsx)
*   **Component**: `Reasoning`

Displays the step-by-step thinking/reasoning of the model inside a collapsible drawer.

### 5.1 Scroll Lock During Streaming
To prevent page jumpiness while reasoning text is streaming in, the component locks the scroll position to the bottom of the viewport using the `useScrollLock` hook:
```typescript
const collapsibleRef = useRef<HTMLDivElement>(null);
const lockScroll = useScrollLock(collapsibleRef, ANIMATION_DURATION);
```
*   **Operation**: Locks the viewport scroll while the drawer expands, keeping the text readable during generation.
