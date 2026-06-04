"use client";

import { useEffect, useState } from "react";
import {
  BookOpen,
  CheckCircle,
  Cpu,
  Database,
  ExternalLink,
  Info,
  Settings,
  Terminal,
} from "lucide-react";

import { GitHubIcon } from "@/components/icons/github";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Item, ItemActions, ItemContent, ItemDescription, ItemMedia, ItemTitle } from "@/components/ui/item";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { InfoAlert } from "@/components/custom-alerts";

export interface UomConfig {
  ollamaHost: string;
  model: string;
  openaiApiUrl: string;
  openaiApiKey: string;
  mssqlConnectionString: string;
  mongodbUri: string;
  neo4jUri: string;
  neo4jPassword: string;
  daytonaTimeout: number;
  dbToolboxUri?: string;
  mongodbMcpUri?: string;
}

const DEFAULT_CONFIG: UomConfig = {
  ollamaHost: "http://localhost:11434",
  model: "einfra/kimi-k2.6",
  openaiApiUrl: "https://llm.ai.e-infra.cz/v1",
  openaiApiKey: "",
  mssqlConnectionString:
    "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True",
  mongodbUri: "mongodb://localhost:27027",
  neo4jUri: "neo4j://localhost:7697",
  neo4jPassword: "password",
  daytonaTimeout: 480,
  dbToolboxUri: "http://localhost:5010",
  mongodbMcpUri: "http://localhost:3010/mcp",
};

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: UomConfig) => void;
}

// Reusable LinkCard Component
interface LinkCardProps {
  icon: React.ComponentType<{ className?: string }>;
  iconClass?: string;
  title: string;
  description: string;
  href: string;
  tooltip: string;
}

function LinkItem({
  icon: Icon,
  iconClass = "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  title,
  description,
  href,
  tooltip,
}: LinkCardProps) {
  return (
    <Item variant="outline">
      <ItemMedia variant="icon" className={iconClass}>
        <Icon className="size-4" />
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{title}</ItemTitle>
        <ItemDescription>
          {description}
        </ItemDescription>
      </ItemContent>
      <ItemActions>
        <TooltipIconButton tooltip={tooltip} side="top">
          <a 
            href={href}
            target="_blank" 
            rel="noreferrer" 
            className="text-primary font-semibold"
          >
            <ExternalLink className="size-4" />
          </a>
        </TooltipIconButton>
      </ItemActions>
    </Item>
  );
}

// Reusable OnboardingStep Component
interface OnboardingStepProps {
  number: number;
  title: string;
  description: string;
  codeCommand?: string;
}

function OnboardingStep({
  number,
  title,
  description,
  codeCommand,
}: OnboardingStepProps) {
  return (
    <div className="flex gap-3 items-start">
      <div className="flex items-center justify-center size-5 rounded-full bg-primary/20 text-primary font-bold text-[11px] shrink-0 mt-0.5 select-none">
        {number}
      </div>
      <div className="space-y-1">
        <h4 className="font-semibold text-foreground">{title}</h4>
        <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>
        {codeCommand && (
          <div className="bg-muted/50 p-2.5 rounded font-mono text-[11px] text-indigo-400 dark:text-indigo-300 border border-border select-all break-all inline-block mt-1.5">
            {codeCommand}
          </div>
        )}
      </div>
    </div>
  );
}

// Reusable ConfigField Component
interface ConfigFieldProps {
  id: keyof UomConfig;
  label: string;
  value: string | number;
  onChange: (key: keyof UomConfig, value: any) => void;
  description: string;
  type?: "text" | "password" | "number" | "textarea";
  placeholder?: string;
}

function ConfigField({
  id,
  label,
  value,
  onChange,
  description,
  type = "text",
  placeholder,
}: ConfigFieldProps) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      {type === "textarea" ? (
        <Textarea
          id={id}
          value={value as string}
          onChange={(e) => onChange(id, e.target.value)}
          className="font-mono text-xs min-h-20"
          placeholder={placeholder}
        />
      ) : (
        <Input
          id={id}
          type={type}
          value={value}
          onChange={(e) => {
            const val = type === "number" ? Number(e.target.value) : e.target.value;
            onChange(id, val);
          }}
          className="font-mono text-xs"
          placeholder={placeholder}
        />
      )}
      <FieldDescription>{description}</FieldDescription>
    </Field>
  );
}

export function ConfigModal({ isOpen, onClose, onSave }: ConfigModalProps) {
  const [config, setConfig] = useState<UomConfig>(DEFAULT_CONFIG);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("uom_translator_config");
      if (saved) {
        try {
          setConfig({ ...DEFAULT_CONFIG, ...JSON.parse(saved) });
        } catch (e) {
          console.error("Error reading saved config", e);
        }
      }
    }
  }, []);

  const handleChange = (key: keyof UomConfig, value: any) => {
    setConfig((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = () => {
    localStorage.setItem("uom_translator_config", JSON.stringify(config));
    localStorage.setItem("uom_config_onboarded", "true");
    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      onSave(config);
      onClose();
    }, 800);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-4xl h-[650px] p-0 overflow-hidden bg-background text-foreground border-border shadow-2xl">
        <DialogTitle className="sr-only">Settings Hub</DialogTitle>
        <DialogDescription className="sr-only">
          Configure settings for Universal Object Mapping
        </DialogDescription>
        
        <Tabs defaultValue="onboarding" orientation="vertical" className="flex h-full w-full">
          {/* Left Navigation Sidebar */}
          <TabsList variant="line" className="w-64 flex flex-col justify-start items-stretch rounded-none border-r border-border bg-muted/5 p-4 h-full shrink-0 gap-1.5">
            <div className="px-3 py-4 mb-4 border-b border-border flex items-center gap-2 select-none">
              <Settings className="size-4 text-primary animate-spin-[spin_3s_linear_infinite]" />
              <span className="font-bold text-sm tracking-tight">UOM Settings</span>
            </div>
            
            <TabsTrigger
              value="onboarding"
              className="justify-start gap-2.5 px-3 py-2 rounded-lg text-left font-medium transition-all"
            >
              <BookOpen className="size-4 shrink-0" />
              <span>Onboarding Guide</span>
            </TabsTrigger>

            <TabsTrigger
              value="llm"
              className="justify-start gap-2.5 px-3 py-2 rounded-lg text-left font-medium transition-all"
            >
              <Cpu className="size-4 shrink-0" />
              <span>LLM Settings</span>
            </TabsTrigger>

            <TabsTrigger
              value="db"
              className="justify-start gap-2.5 px-3 py-2 rounded-lg text-left font-medium transition-all"
            >
              <Database className="size-4 shrink-0" />
              <span>Database URIs</span>
            </TabsTrigger>

            <TabsTrigger
              value="daytona"
              className="justify-start gap-2.5 px-3 py-2 rounded-lg text-left font-medium transition-all"
            >
              <Terminal className="size-4 shrink-0" />
              <span>Daytona Sandbox</span>
            </TabsTrigger>
          </TabsList>

          {/* Right Content Pane */}
          <div className="flex-1 flex flex-col min-w-0 h-full bg-background relative">
            <div className="flex-1 overflow-hidden relative">
              
              {/* Onboarding Content */}
              <TabsContent 
                value="onboarding" 
                className="absolute inset-0 overflow-y-auto custom-scrollbar p-6 space-y-6 mt-0"
              >
                <div className="space-y-2">
                  <h2 className="font-bold text-foreground">Getting Started with UOM</h2>
                  <p className="text-muted-foreground leading-relaxed">
                    Universal Object Mapping (UOM) is an advanced research and engineering platform designed to automate the translation, validation, and performance optimization of database schemas and query code from relational .NET ORM frameworks to NoSQL document/graph-based Java Spring Data paradigms.
                  </p>
                </div>

                <InfoAlert title="Critical Setup Prerequisite" 
                  description={
                    <div>Your local database stack, MCP services, and Daytona daemon <strong>must be active and configured</strong> before executing migrations. The orchestrator connects directly to them to inspect schemas, build mapping rules, compile validation harnesses, and evaluate query results.</div>
                  }
                />

                <div className="space-y-3">
                  <h3 className="font-bold text-foreground uppercase tracking-wider select-none">How to Configure UOM</h3>
                  
                  <div className="grid gap-4 text-xs">
                    <OnboardingStep
                      number={1}
                      title="Boot the Database Stack"
                      description="Run the docker-compose services inside the monorepo root directory. This spins up MS SQL Server (source), MongoDB & Neo4j (targets), MongoDB Relational Migrator, and the GenAI DB Toolbox and MongoDB MCP Servers."
                      codeCommand="docker compose up -d --build"
                    />
                    <OnboardingStep
                      number={2}
                      title="Configure LLM Orchestration"
                      description="Specify your LLM provider under the LLM Settings tab. You can use Metacentrum e-INFRA CZ (fill in the API key and URL) or host a local model using Ollama (e.g. running qwen3-coder:30b)."
                    />
                    <OnboardingStep
                      number={3}
                      title="Set Connection Mappings & Daytona"
                      description="Verify the MS SQL connection strings and target database URIs under Database URIs. Set compiler timeouts under Daytona Sandbox. The Daytona daemon compiles and builds test packages inside secure containers."
                    />
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <h3 className="font-bold text-foreground uppercase tracking-wider select-none">Setup Tools &amp; Links</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <LinkItem
                      icon={BookOpen}
                      title="GitHub Codebase"
                      description="Universal Object Mapping GitHub Repository"
                      href="https://github.com/corovcam/Universal-Object-Mapping"
                      tooltip="Universal Object Mapping GitHub Repository"
                    />
                    <LinkItem
                      icon={Database}
                      iconClass="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      title="MongoDB Relational Migrator"
                      description="MongoDB Relational Migrator Dashboard"
                      href="http://localhost:8091"
                      tooltip="Open MongoDB Relational Migrator Web UI"
                    />
                    <LinkItem
                      icon={Database}
                      iconClass="bg-blue-500/10 text-blue-400 border-blue-500/20"
                      title="Neo4j ETL Tool Docs"
                      description="Neo4j ETL Tool setup guide"
                      href="https://neo4j.com/developer/neo4j-etl/"
                      tooltip="Open Neo4j ETL Tool Documentation"
                    />
                    <LinkItem
                      icon={Terminal}
                      iconClass="bg-orange-500/10 text-orange-400 border-orange-500/20"
                      title="Neo4j Console"
                      description="Browser Cypher Console"
                      href="http://localhost:7474"
                      tooltip="Open Neo4j Console"
                    />
                  </div>
                </div>
              </TabsContent>

              {/* LLM Settings Content */}
              <TabsContent 
                value="llm" 
                className="absolute inset-0 overflow-y-auto custom-scrollbar p-6 space-y-6 mt-0"
              >
                <div>
                  <h2 className="font-bold text-foreground">LLM Orchestration Settings</h2>
                  <p className="text-muted-foreground">Specify backend model selectors and API endpoints.</p>
                </div>

                <FieldGroup>
                  <ConfigField
                    id="ollamaHost"
                    label="Ollama Endpoint URL"
                    value={config.ollamaHost}
                    onChange={handleChange}
                    description="The URI where your local Ollama instance is hosted."
                    placeholder="e.g. http://localhost:11434"
                  />

                  <ConfigField
                    id="model"
                    label="Target Translation LLM Model"
                    value={config.model}
                    onChange={handleChange}
                    description="Must match the provider/name paradigm (e.g. einfra/kimi-k2.6 or ollama/qwen3-coder:30b)."
                    placeholder="ollama/qwen3-coder:30b"
                  />

                  <Separator className="my-2" />

                  <ConfigField
                    id="openaiApiUrl"
                    label="E-Infra API Base URL (Optional)"
                    value={config.openaiApiUrl}
                    onChange={handleChange}
                    description="OpenAI-compatible endpoints provided by E-Infra API."
                    placeholder="https://einfra.net/v1"
                  />

                  <ConfigField
                    id="openaiApiKey"
                    type="password"
                    label="E-Infra API Secret Token"
                    value={config.openaiApiKey}
                    onChange={handleChange}
                    description="API key used for authenticating with the E-Infra model provider."
                    placeholder="Enter API key"
                  />
                </FieldGroup>
              </TabsContent>

              {/* Database URIs Content */}
              <TabsContent 
                value="db" 
                className="absolute inset-0 overflow-y-auto custom-scrollbar p-6 space-y-6 mt-0"
              >
                <div>
                  <h2 className="font-bold text-foreground">Database Connection Mappings</h2>
                  <p className="text-muted-foreground">Define URIs where target databases and caches reside.</p>
                </div>

                <FieldGroup>
                  <ConfigField
                    id="mssqlConnectionString"
                    type="textarea"
                    label="MS SQL Server Connection String"
                    value={config.mssqlConnectionString}
                    onChange={handleChange}
                    description="Connection details for the source relational MS SQL Server database."
                    placeholder="Server=localhost,1333;Database=..."
                  />

                  <ConfigField
                    id="mongodbUri"
                    label="MongoDB Target URI"
                    value={config.mongodbUri}
                    onChange={handleChange}
                    description="The connection URI for the target document-based MongoDB."
                    placeholder="mongodb://..."
                  />

                  <div className="grid grid-cols-2 gap-4">
                    <ConfigField
                      id="neo4jUri"
                      label="Neo4j Target URI"
                      value={config.neo4jUri}
                      onChange={handleChange}
                      description="The connection URI for the target graph-based Neo4j database."
                      placeholder="neo4j://..."
                    />

                    <ConfigField
                      id="neo4jPassword"
                      type="password"
                      label="Neo4j Database Password"
                      value={config.neo4jPassword}
                      onChange={handleChange}
                      description="Password for Neo4j authentication."
                      placeholder="password"
                    />
                  </div>

                  <Separator className="my-2" />

                  <div className="grid grid-cols-2 gap-4">
                    <ConfigField
                      id="dbToolboxUri"
                      label="Database Toolbox MCP URI"
                      value={config.dbToolboxUri || ""}
                      onChange={handleChange}
                      description="Optional DB inspection server URI."
                      placeholder="e.g. http://localhost:8000"
                    />

                    <ConfigField
                      id="mongodbMcpUri"
                      label="MongoDB MCP URI"
                      value={config.mongodbMcpUri || ""}
                      onChange={handleChange}
                      description="Optional MongoDB inspection server URI."
                      placeholder="e.g. http://localhost:8001"
                    />
                  </div>
                </FieldGroup>
              </TabsContent>

              {/* Daytona Sandbox Content */}
              <TabsContent 
                value="daytona" 
                className="absolute inset-0 overflow-y-auto custom-scrollbar p-6 space-y-6 mt-0"
              >
                <div>
                  <h2 className="font-bold text-foreground">Daytona Dev Sandbox</h2>
                  <p className="text-muted-foreground">Define compiler timeouts and Daytona workspace rules.</p>
                </div>

                <FieldGroup>
                  <ConfigField
                    id="daytonaTimeout"
                    type="number"
                    label="Sandbox Build Timeout (seconds)"
                    value={config.daytonaTimeout}
                    onChange={handleChange}
                    description="Time allowed for .NET and Spring compilation & verification runs inside the container."
                  />

                  <InfoAlert 
                    title="Daytona Local Sandbox Mode" 
                    description="Daytona is automatically loaded and configured in the devcontainer environment. Target compilation builds run securely in parallel sandbox environments to ensure generated C# queries and target Java spring mappings build successfully before comparing data equivalence."
                    Icon={Terminal}
                  />
                </FieldGroup>
              </TabsContent>

            </div>

            {/* Shared Footer */}
            <div className="p-4 border-t border-border bg-muted/10 flex items-center justify-between shrink-0 select-none">
              <span className="text-xs text-muted-foreground">Universal Object Mapping Translator v0.1</span>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  onClick={onClose}
                  className="text-xs px-3 h-8"
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleSave}
                  disabled={saveSuccess}
                  className="bg-sidebar-primary hover:bg-sidebar-primary/80 text-white font-medium text-xs px-4 h-8 flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
                >
                  {saveSuccess ? (
                    <>
                      <CheckCircle className="size-3.5 animate-bounce" />
                      <span>Saved!</span>
                    </>
                  ) : (
                    <>
                      <Settings className="size-3.5" />
                      <span>Save Settings</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
