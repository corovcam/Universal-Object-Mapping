"use client";

import {
	useLangGraphInterruptState,
	useLangGraphSendCommand,
} from "@assistant-ui/react-langgraph";
import {
	AlertTriangle,
	Check,
	MessageSquare,
	RefreshCw,
	Sparkles,
	X,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

/**
 * Shape of the payload the backend surfaces through LangGraph's native `interrupt()`
 * call inside `human_intervention_node`. Mirrors the dict passed to `interrupt(...)`.
 */
type InterventionPayload = {
	instruction?: string;
	state?: {
		translated_query_code?: string | null;
		translated_schema_code?: string | null;
		explanation_message?: string | null;
		query_equivalence_deep_diffs?: unknown;
	};
};

/**
 * Resume value expected by the backend. Validated server-side against the
 * `HumanInterventionResponse` Pydantic model (both fields are required), so it
 * must be sent as an object — not a bare string or a JSON-encoded string.
 */
type HumanInterventionResume = {
	decision: "accept" | "reject";
	feedback: string;
};

/**
 * Renders any value (string or structured object) as readable monospace text.
 */
function renderValue(value: unknown): string {
	if (value == null) return "";
	return typeof value === "object"
		? JSON.stringify(value, null, 2)
		: String(value);
}

/**
 * React Component to handle the LangGraph suspended (interrupted) state.
 *
 * Intercepts the human-in-the-loop validation checkpoint raised by the backend
 * `human_intervention_node` via LangGraph's native `interrupt()` API. The payload
 * (instruction + current translation state + query-equivalence deep diffs) is
 * surfaced through `useLangGraphInterruptState()`. The user can Accept the
 * translation or Reject it with targeted feedback; the decision is resumed back
 * into the graph with `Command(resume={ decision, feedback })`.
 *
 * The interrupt is captured live (requires `"updates"` in the stream's `streamMode`)
 * and restored on reload via the runtime's `load()` callback, so the card reappears
 * when an interrupted conversation is reopened from the thread list.
 *
 * @returns {React.JSX.Element | null} The interrupt control card, or null if execution is not suspended.
 */
export function InterruptHandler() {
	/** Current graph suspension payload, or undefined when not interrupted. */
	const interrupt = useLangGraphInterruptState();
	/** Hook to submit the user's decision and resume the LangGraph flow. */
	const sendCommand = useLangGraphSendCommand();

	const [decision, setDecision] = useState<"accept" | "reject" | null>(null);
	const [feedback, setFeedback] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);

	// Note: do NOT gate on `interrupt.resumable` — that field is deprecated in the
	// LangGraph SDK (>=1.x) and omitted by recent servers, which previously hid the
	// card entirely. Render whenever there is an interrupt payload to act on.
	if (!interrupt?.value) return null;

	const payload = (interrupt.value ?? {}) as InterventionPayload;
	const instruction = payload.instruction;
	const interventionState = payload.state ?? {};
	const deepdiff = interventionState.query_equivalence_deep_diffs ?? null;
	const explanation = interventionState.explanation_message ?? null;

	/**
	 * Form submit handler. Resumes the LangGraph graph with the user's decision.
	 * The resume value is an object matching the backend `HumanInterventionResponse`
	 * model: `feedback` is required, so it is sent as an empty string on accept.
	 *
	 * @param {React.FormEvent} e - Form event.
	 */
	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!decision) return;
		setIsSubmitting(true);
		try {
			const resume: HumanInterventionResume =
				decision === "accept"
					? { decision: "accept", feedback: "" }
					: { decision: "reject", feedback };
			// `LangGraphCommand.resume` is typed as `string` upstream, but LangGraph
			// forwards the value verbatim to the server, which validates it against the
			// `HumanInterventionResponse` model (an object). Cast past the narrow type.
			await sendCommand({ resume: resume as unknown as string });
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
						{instruction ||
							"The translation process reached the maximum automatic retries. Relational equivalence checks require manual validation or targeted correction."}
					</span>
				</div>
			</div>

			<form onSubmit={handleSubmit} className="space-y-4 p-4">
				{explanation && (
					<div className="space-y-1.5">
						<span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
							Translation Explanation
						</span>
						<div className="custom-scrollbar max-h-36 select-text overflow-y-auto rounded-lg border bg-muted p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
							{renderValue(explanation)}
						</div>
					</div>
				)}

				{deepdiff != null &&
					!(
						typeof deepdiff === "object" && Object.keys(deepdiff).length === 0
					) && (
						<div className="space-y-1.5">
							<span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
								Query Equivalence DeepDiff
							</span>
							<div className="custom-scrollbar max-h-32 select-text overflow-y-auto rounded-lg border bg-muted p-3 font-mono text-[10px] leading-relaxed text-destructive">
								{renderValue(deepdiff)}
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
						<label
							htmlFor="correction-textarea"
							className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground"
						>
							<MessageSquare className="size-3.5 text-primary" />
							Targeted Agent Correction Pointers
						</label>
						<textarea
							id="correction-textarea"
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
