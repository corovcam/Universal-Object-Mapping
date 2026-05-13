import { ChatWidget } from "@/components/chat";

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      {/* Background Pattern */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(99,102,241,0.08),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(99,102,241,0.05),transparent_50%)]" />
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%236366f1' fill-opacity='0.03'%3E%3Cpath d='m36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
      </div>

      {/* Header - simulating ORMorpher app background */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                <svg
                  className="size-5 text-primary"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18" />
                  <path d="M9 21V9" />
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-foreground">ORMorpher</h1>
                <p className="text-xs text-muted-foreground">Universal Object Mapping</p>
              </div>
            </div>
            <nav className="flex items-center gap-6">
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Documentation</a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">API</a>
              <a href="#" className="text-sm text-primary font-medium">LLM Advisor</a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content - simulating background app */}
      <div className="container mx-auto px-6 py-12">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Hero Section */}
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold text-foreground">
              Framework-Agnostic Database Migration
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Translate your ORM schemas and queries between .NET and Java frameworks using 
              AI-powered code generation with LangGraph orchestration.
            </p>
          </div>

          {/* Feature Cards */}
          <div className="grid gap-6 md:grid-cols-3">
            <div className="p-6 rounded-xl border border-border bg-card/50">
              <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <svg className="size-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                  <polyline points="14,2 14,8 20,8" />
                  <path d="M12 18v-6" />
                  <path d="m9 15 3 3 3-3" />
                </svg>
              </div>
              <h3 className="font-semibold text-foreground mb-2">Schema Translation</h3>
              <p className="text-sm text-muted-foreground">
                Convert Entity Framework Core, NHibernate, or Dapper entities to Spring Data MongoDB or Neo4j.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-border bg-card/50">
              <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <svg className="size-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
                  <path d="M21 3v5h-5" />
                </svg>
              </div>
              <h3 className="font-semibold text-foreground mb-2">Iterative Refinement</h3>
              <p className="text-sm text-muted-foreground">
                Automatic validation and error correction through sandboxed compilation environments.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-border bg-card/50">
              <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <svg className="size-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
              </div>
              <h3 className="font-semibold text-foreground mb-2">Query Migration</h3>
              <p className="text-sm text-muted-foreground">
                Transform LINQ queries to MongoTemplate or Cypher with semantic equivalence.
              </p>
            </div>
          </div>

          {/* Supported Frameworks */}
          <div className="p-6 rounded-xl border border-border bg-card/50">
            <h3 className="font-semibold text-foreground mb-4">Supported Frameworks</h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs uppercase tracking-wide text-muted-foreground mb-3">Source (.NET)</h4>
                <ul className="space-y-2">
                  <li className="flex items-center gap-2 text-sm text-foreground">
                    <span className="size-1.5 rounded-full bg-primary" />
                    Entity Framework Core
                  </li>
                  <li className="flex items-center gap-2 text-sm text-foreground">
                    <span className="size-1.5 rounded-full bg-primary" />
                    NHibernate
                  </li>
                  <li className="flex items-center gap-2 text-sm text-foreground">
                    <span className="size-1.5 rounded-full bg-primary" />
                    Dapper
                  </li>
                </ul>
              </div>
              <div>
                <h4 className="text-xs uppercase tracking-wide text-muted-foreground mb-3">Target (Java)</h4>
                <ul className="space-y-2">
                  <li className="flex items-center gap-2 text-sm text-foreground">
                    <span className="size-1.5 rounded-full bg-success" />
                    Spring Data MongoDB
                  </li>
                  <li className="flex items-center gap-2 text-sm text-foreground">
                    <span className="size-1.5 rounded-full bg-success" />
                    Spring Data Neo4j
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Instructions */}
          <div className="text-center text-muted-foreground text-sm">
            <p>Click the chat widget in the bottom-right corner to start a translation.</p>
          </div>
        </div>
      </div>

      {/* LLM Advisor Chat Widget */}
      <ChatWidget />
    </main>
  );
}
