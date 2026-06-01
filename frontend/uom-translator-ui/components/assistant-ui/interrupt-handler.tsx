"use client";

import { useLangGraphInterruptState, useLangGraphSendCommand } from "@assistant-ui/react-langgraph";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  Check,
  X,
  RefreshCw,
  Sparkles,
  MessageSquare,
} from "lucide-react";

export function InterruptHandler() {
  const interrupt = useLangGraphInterruptState();
  const sendCommand = useLangGraphSendCommand();
  const [decision, setDecision] = useState<"accept" | "reject" | null>(null);
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!interrupt?.resumable) return null;

  const payload = interrupt.value ?? {};
  const validationErrors = payload?.validation_errors || payload?.error || null;
  const deepdiffText = payload?.query_equivalence_deep_diffs || null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!decision) return;
    setIsSubmitting(true);
    try {
      const resume = decision === "accept"
        ? "accept"
        : JSON.stringify({ decision: "reject", feedback });
      await sendCommand({ resume });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-4 mb-3 rounded-xl border border-amber-500/20 bg-background shadow-2xl overflow-hidden">
      {/* Alert Banner */}
      <div className="flex items-start gap-3 border-b border-amber-500/20 bg-amber-500/10 p-4">
        <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-500" />
        <div>
          <span className="block text-xs font-bold text-foreground">
            Agent Execution Suspended
          </span>
          <span className="mt-0.5 block text-[10px] leading-relaxed text-muted-foreground">
            The translation process reached the maximum automatic retries.
            Relational equivalence checks require manual validation or
            targeted correction.
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 p-4">
        {validationErrors && (
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Validation Failures
            </span>
            <div className="custom-scrollbar max-h-36 select-text overflow-y-auto rounded-lg border bg-muted p-3 font-mono text-[10px] leading-relaxed text-destructive">
              {typeof validationErrors === "object"
                ? JSON.stringify(validationErrors, null, 2)
                : validationErrors}
            </div>
          </div>
        )}

        {deepdiffText && (
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Equivalence DeepDiff Payload
            </span>
            <div className="custom-scrollbar max-h-32 select-text overflow-y-auto rounded-lg border bg-muted p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
              {typeof deepdiffText === "object"
                ? JSON.stringify(deepdiffText, null, 2)
                : deepdiffText}
            </div>
          </div>
        )}

        <div className="space-y-3">
          <span className="block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Decision Assessment
          </span>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setDecision("accept");
                setFeedback("");
              }}
              className={`flex flex-col items-center justify-center rounded-lg border p-3 text-center text-xs transition-all ${
                decision === "accept"
                  ? "border-emerald-500 bg-emerald-500/10 font-bold text-emerald-400 shadow-lg shadow-emerald-500/10"
                  : "border-border bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              <Check className="mb-1.5 size-5 shrink-0" />
              <span>Accept &amp; Save</span>
              <span className="mt-0.5 text-[9px] font-normal text-muted-foreground">
                Proceed with final schema mapping output
              </span>
            </button>

            <button
              type="button"
              onClick={() => setDecision("reject")}
              className={`flex flex-col items-center justify-center rounded-lg border p-3 text-center text-xs transition-all ${
                decision === "reject"
                  ? "border-rose-500 bg-rose-500/10 font-bold text-rose-400 shadow-lg shadow-rose-500/10"
                  : "border-border bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              <X className="mb-1.5 size-5 shrink-0" />
              <span>Reject &amp; Correct</span>
              <span className="mt-0.5 text-[9px] font-normal text-muted-foreground">
                Supply direct pointers and re-trigger generation
              </span>
            </button>
          </div>
        </div>

        {decision === "reject" && (
          <div className="space-y-1.5 animate-in fade-in duration-200">
            <label className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              <MessageSquare className="size-3.5 text-primary" />
              Targeted Agent Correction Pointers
            </label>
            <textarea
              required
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Provide clear hints explaining what needs fixing..."
              className="w-full resize-none rounded-lg border bg-muted p-3 font-sans text-xs leading-relaxed text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
          </div>
        )}

        {decision && (
          <Button
            type="submit"
            disabled={isSubmitting}
            className={`flex h-9 w-full items-center justify-center gap-2 rounded-lg text-xs font-bold shadow-lg transition-all ${
              decision === "accept"
                ? "bg-emerald-600 text-white shadow-emerald-600/15 hover:bg-emerald-500"
                : "bg-rose-600 text-white shadow-rose-600/15 hover:bg-rose-500"
            }`}
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="size-3.5 animate-spin" />
                <span>Resuming execution...</span>
              </>
            ) : (
              <>
                <Sparkles className="size-3.5" />
                <span>Submit decision to pipeline</span>
              </>
            )}
          </Button>
        )}
      </form>
    </div>
  );
}
