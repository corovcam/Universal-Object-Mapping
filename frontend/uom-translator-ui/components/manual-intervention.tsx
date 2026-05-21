"use client";

import React, { useState } from "react";
import { 
  AlertTriangle, 
  Check, 
  X, 
  HelpCircle, 
  MessageSquare,
  Sparkles,
  RefreshCw,
  Info
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface ManualInterventionProps {
  interruptPayload: any;
  onSubmitResponse: (decision: "accept" | "reject", feedback: string) => void;
  isSubmitting: boolean;
}

export function ManualIntervention({
  interruptPayload,
  onSubmitResponse,
  isSubmitting
}: ManualInterventionProps) {
  const [decision, setDecision] = useState<"accept" | "reject" | null>(null);
  const [feedback, setFeedback] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!decision) return;
    onSubmitResponse(decision, feedback);
  };

  const hasPayloadDetails = !!interruptPayload;
  const validationErrors = interruptPayload?.validation_errors || interruptPayload?.error || null;
  const deepdiffText = interruptPayload?.query_equivalence_deep_diffs || null;

  return (
    <div className="w-full bg-slate-950 border border-amber-500/20 rounded-xl overflow-hidden shadow-2xl glow-indigo">
      {/* Alert Banner */}
      <div className="bg-amber-500/10 border-b border-amber-500/20 p-4 flex items-start gap-3">
        <AlertTriangle className="size-5 text-amber-500 shrink-0 mt-0.5" />
        <div>
          <span className="text-xs font-bold text-slate-100 block">Agent Execution Suspended</span>
          <span className="text-[10px] text-slate-400 block mt-0.5 leading-relaxed">
            The translation process reached the maximum automatic retries (3 attempts). Relational equivalence checks require manual validation or targeted correction.
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="p-4 space-y-4">
        {/* Validation Errors description */}
        {validationErrors && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Validation Failures</span>
            <div className="bg-slate-900 border border-slate-850 rounded-lg p-3 font-mono text-[10px] text-rose-400 max-h-36 overflow-y-auto custom-scrollbar select-text leading-relaxed">
              {typeof validationErrors === "object" ? JSON.stringify(validationErrors, null, 2) : validationErrors}
            </div>
          </div>
        )}

        {/* Deep diff summary */}
        {deepdiffText && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Equivalence DeepDiff payload</span>
            <div className="bg-slate-900 border border-slate-850 rounded-lg p-3 font-mono text-[10px] text-slate-400 max-h-32 overflow-y-auto custom-scrollbar select-text leading-relaxed">
              {typeof deepdiffText === "object" ? JSON.stringify(deepdiffText, null, 2) : deepdiffText}
            </div>
          </div>
        )}

        {/* Decision Controls */}
        <div className="space-y-3">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">Decision Assessment</span>
          
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setDecision("accept");
                // Clear feedback on accept as it's not needed
                setFeedback("");
              }}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border text-center transition-all ${
                decision === "accept"
                  ? "bg-emerald-500/10 border-emerald-500 text-emerald-400 font-bold shadow-lg shadow-emerald-500/10"
                  : "bg-slate-900 border-slate-850 text-slate-450 hover:text-slate-200"
              }`}
            >
              <Check className="size-5 mb-1.5 shrink-0" />
              <span className="text-xs">Accept &amp; Save</span>
              <span className="text-[9px] text-slate-500 font-normal mt-0.5">Proceed with final schema mapping output</span>
            </button>

            <button
              type="button"
              onClick={() => setDecision("reject")}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border text-center transition-all ${
                decision === "reject"
                  ? "bg-rose-500/10 border-rose-500 text-rose-400 font-bold shadow-lg shadow-rose-500/10"
                  : "bg-slate-900 border-slate-850 text-slate-450 hover:text-slate-200"
              }`}
            >
              <X className="size-5 mb-1.5 shrink-0" />
              <span className="text-xs">Reject &amp; Correct</span>
              <span className="text-[9px] text-slate-500 font-normal mt-0.5">Supply direct pointers and re-trigger generation</span>
            </button>
          </div>
        </div>

        {/* Feedback description textbox */}
        {decision === "reject" && (
          <div className="space-y-1.5 animate-in fade-in duration-200">
            <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block flex items-center gap-1.5">
              <MessageSquare className="size-3.5 text-indigo-400" />
              Targeted Agent Correction Pointers
            </label>
            <textarea
              required
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Provide clear hints explaining what needs fixing (e.g. 'Use spring @Query annotation for custom cypher search', 'Ensure Mongo document indexes relate properly')"
              className="w-full bg-slate-900 border border-slate-850 rounded-lg p-3 text-xs focus:outline-none focus:border-indigo-500 font-sans text-slate-200 resize-none leading-relaxed"
            />
          </div>
        )}

        {/* Action Button */}
        {decision && (
          <Button
            type="submit"
            disabled={isSubmitting}
            className={`w-full font-bold text-xs h-9 rounded-lg flex items-center justify-center gap-2 shadow-lg transition-all ${
              decision === "accept"
                ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/15"
                : "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/15"
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
