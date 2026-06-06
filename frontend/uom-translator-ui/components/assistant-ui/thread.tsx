"use-client";

import {
	ActionBarMorePrimitive,
	ActionBarPrimitive,
	AuiIf,
	ComposerPrimitive,
	ErrorPrimitive,
	groupPartByType,
	MessagePrimitive,
	SuggestionPrimitive,
	ThreadPrimitive,
	useAuiState,
} from "@assistant-ui/react";
import {
	ArrowDownIcon,
	ArrowUpIcon,
	BotIcon,
	CheckIcon,
	ChevronRightIcon,
	CopyIcon,
	DownloadIcon,
	LoaderIcon,
	Maximize2,
	Minimize2,
	MoreHorizontalIcon,
	RefreshCwIcon,
	SquareIcon,
	UserIcon,
	X,
} from "lucide-react";
import { Allow, parse as parsePartialJson } from "partial-json";
import { ScrollArea as ScrollAreaPrimitive } from "radix-ui";
import { type FC, Suspense, useEffect, useState } from "react";
import { UserMessageAttachments } from "@/components/assistant-ui/attachment";
import { InterruptHandler } from "@/components/assistant-ui/interrupt-handler";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import {
	Reasoning,
	ReasoningContent,
	ReasoningRoot,
	ReasoningText,
	ReasoningTrigger,
} from "@/components/assistant-ui/reasoning";
import { ToolFallback } from "@/components/assistant-ui/tool-fallback";
import {
	ToolGroupContent,
	ToolGroupRoot,
	ToolGroupTrigger,
} from "@/components/assistant-ui/tool-group";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { ErrorAlert } from "@/components/custom-alerts";
import { AutoScrollJsonViewer } from "@/components/json-viewer";
import { Button } from "@/components/ui/button";
import { ScrollBar } from "@/components/ui/scroll-area";
import { SkeletonText } from "@/components/ui/skeleton";
import { useGraphStateContext } from "@/hooks/use-graph-state-context";
import { cn } from "@/lib/utils";

export const Thread: FC = () => {
	return (
		<ScrollAreaPrimitive.Root asChild>
			<ThreadPrimitive.Root
				className="aui-root aui-thread-root @container flex h-full flex-col bg-background"
				style={{
					["--thread-max-width" as string]: "44rem",
					["--composer-radius" as string]: "24px",
					["--composer-padding" as string]: "10px",
				}}
			>
				<ScrollAreaPrimitive.Viewport
					className="thread-viewport h-full"
					asChild
				>
					<ThreadPrimitive.Viewport
						autoScroll
						turnAnchor="bottom"
						data-slot="aui_thread-viewport"
						className="relative flex flex-1 flex-col overflow-x-auto overflow-y-auto scroll-smooth h-full"
					>
						<div className="mx-auto flex w-full max-w-(--thread-max-width) flex-1 flex-col px-4 pt-4">
							<AuiIf condition={(s) => s.thread.isEmpty}>
								<ThreadWelcome />
							</AuiIf>

							<div
								data-slot="aui_message-group"
								className="mb-10 flex flex-col gap-y-8 empty:hidden"
							>
								<ThreadPrimitive.Messages>
									{() => <ThreadMessage />}
								</ThreadPrimitive.Messages>
							</div>

							<InterruptHandler />

							<GlobalErrorMessage />

							<ThreadPrimitive.ViewportFooter className="aui-thread-viewport-footer sticky bottom-0 mt-auto flex flex-col gap-4 overflow-visible rounded-t-(--composer-radius) bg-background pb-4 md:pb-6">
								<ThreadScrollToBottom />
								<Composer />
							</ThreadPrimitive.ViewportFooter>
						</div>
					</ThreadPrimitive.Viewport>
				</ScrollAreaPrimitive.Viewport>
				<ScrollBar className="custom-scrollbar" />
			</ThreadPrimitive.Root>
		</ScrollAreaPrimitive.Root>
	);
};

const GlobalErrorMessage: FC = () => {
	const { error, setError } = useGraphStateContext();
	if (!error) return null;
	return (
		<ErrorAlert
			title={error.message || "An error occurred"}
			description={error.error?.message}
			className="sticky bottom-0 mt-auto mb-3 rounded-(--composer-radius) no-scrollbar"
			action={
				<TooltipIconButton
					tooltip="Dismiss error"
					side="top"
					size="xs"
					onClick={() => setError(null)}
				>
					<X className="size-4" />
				</TooltipIconButton>
			}
		/>
	);
};

const isIntermediatePrompt = (text: string): boolean => {
	if (!text) return false;
	const lower = text.toLowerCase();
	return (
		// lower.includes("commencing validation") ||
		// lower.includes("commencing parallel validation") ||
		// lower.includes("commencing query equivalence") ||
		// lower.includes("successfully extracted inputs") ||
		// lower.includes(
		// 	"generated translation. commencing deterministic validation",
		// ) ||
		// lower.includes("schema inspection completed successfully") ||
		lower.includes("inspect the database schemas") ||
		lower.includes("evaluate the following validation results") ||
		lower.includes("analyze the following conversation") ||
		lower.includes("translate the following source code")
	);
};

const getPromptTitle = (text: string): string => {
	const lowerText = text.toLowerCase();
	if (lowerText.includes("inspect the database schemas")) {
		return "Database Schema Inspector Prompt";
	}
	if (lowerText.includes("evaluate the following validation results")) {
		return "LLM Evaluation Prompt";
	}
	if (lowerText.includes("translate the following source code")) {
		return "Code Translation Prompt";
	}
	if (lowerText.includes("analyze the following conversation")) {
		return "Extraction Prompt";
	}
	return "System Prompt";
};

const ThreadMessage = () => {
	const isEditing = useAuiState((s) => s.message.composer.isEditing);
	const role = useAuiState((s) => s.message.role);

	if (isEditing) return <EditComposer />;

	if (role === "user") return <UserMessage />;
	return <AssistantMessage />;
};

const ThreadScrollToBottom: FC = () => {
	return (
		<ThreadPrimitive.ScrollToBottom asChild>
			<TooltipIconButton
				tooltip="Scroll to bottom"
				variant="outline"
				className="aui-thread-scroll-to-bottom absolute -top-12 z-10 self-center rounded-full p-4 disabled:invisible dark:border-border dark:bg-background dark:hover:bg-accent"
			>
				<ArrowDownIcon />
			</TooltipIconButton>
		</ThreadPrimitive.ScrollToBottom>
	);
};

const ThreadWelcome: FC = () => {
	return (
		<div className="aui-thread-welcome-root my-auto flex grow flex-col">
			<div className="aui-thread-welcome-center flex w-full grow flex-col items-center justify-center">
				<div className="aui-thread-welcome-message flex size-full flex-col justify-center px-4">
					<h1 className="aui-thread-welcome-message-inner fade-in slide-in-from-bottom-1 animate-in fill-mode-both font-semibold text-2xl duration-200 text-primary">
						<span className="shimmer shimmer-color-neutral-400 shimmer-spread-200 text-primary shimmer-angle-75">
							Welcome to{" "}
							<span className="font-bold bg-clip-text">
								Universal Object Mapping
							</span>{" "}
							Assistant!
						</span>
					</h1>
					<p className="aui-thread-welcome-message-inner fade-in slide-in-from-bottom-1 animate-in fill-mode-both text-muted-foreground text-xl delay-75 duration-200">
						Use the below sample translation suggestions or write your own.
					</p>
				</div>
			</div>
			<Suspense fallback={<SkeletonText count={3} />}>
				<ThreadSuggestions />
			</Suspense>
		</div>
	);
};

const ThreadSuggestions: FC = () => {
	return (
		<div className="aui-thread-welcome-suggestions grid w-full @md:grid-cols-2 gap-2 pb-4">
			<ThreadPrimitive.Suggestions>
				{() => <ThreadSuggestionItem />}
			</ThreadPrimitive.Suggestions>
		</div>
	);
};

const ThreadSuggestionItem: FC = () => {
	return (
		<div className="aui-thread-welcome-suggestion-display fade-in slide-in-from-bottom-2 @md:nth-[n+3]:block nth-[n+3]:hidden animate-in fill-mode-both duration-200">
			<SuggestionPrimitive.Trigger send={false} asChild>
				<Button
					variant="ghost"
					className="aui-thread-welcome-suggestion h-auto w-full @md:flex-col flex-wrap items-start justify-start gap-1 rounded-3xl border bg-background px-4 py-3 text-start text-sm transition-colors hover:bg-muted text-primary"
				>
					<SuggestionPrimitive.Title className="aui-thread-welcome-suggestion-text-1 font-medium" />
					<SuggestionPrimitive.Description className="aui-thread-welcome-suggestion-text-2 text-muted-foreground empty:hidden text-wrap" />
				</Button>
			</SuggestionPrimitive.Trigger>
		</div>
	);
};

const Composer: FC = () => {
	const [expanded, setExpanded] = useState(false);

	return (
		<ComposerPrimitive.Root className="aui-composer-root relative flex w-full flex-col text-primary">
			<ComposerPrimitive.AttachmentDropzone asChild>
				<div
					data-slot="aui_composer-shell"
					className="flex w-full flex-col gap-2 rounded-(--composer-radius) border bg-background p-(--composer-padding) transition-shadow focus-within:border-ring/75 focus-within:ring-2 focus-within:ring-ring/20 data-[dragging=true]:border-ring data-[dragging=true]:border-dashed data-[dragging=true]:bg-accent/50"
				>
					<div className="relative flex items-center justify-between">
						{/* <ComposerAttachments /> */}
						<TooltipIconButton
							tooltip={expanded ? "Collapse input" : "Expand input"}
							side="bottom"
							type="button"
							variant="ghost"
							size="icon"
							className="size-8 rounded-full self-end"
							aria-label={expanded ? "Collapse input" : "Expand input"}
							onClick={() => setExpanded((e) => !e)}
						>
							{expanded ? (
								<Minimize2 className="size-4 stroke-[1.5px]" />
							) : (
								<Maximize2 className="size-4 stroke-[1.5px]" />
							)}
						</TooltipIconButton>
					</div>

					<ComposerPrimitive.Input
						placeholder="Send a message..."
						className={`aui-composer-input custom-scrollbar w-full resize-none bg-transparent px-1.75 py-1 text-sm outline-none placeholder:text-muted-foreground/80 ${expanded ? "min-h-40 max-h-70" : "min-h-10 max-h-32"}`}
						rows={1}
						autoFocus
						aria-label="Message input"
					/>
					<ComposerAction />
				</div>
			</ComposerPrimitive.AttachmentDropzone>
		</ComposerPrimitive.Root>
	);
};

const ComposerAction: FC = () => {
	return (
		<div className="aui-composer-action-wrapper relative flex items-center justify-end">
			{/* <ComposerAddAttachment /> */}
			<AuiIf condition={(s) => !s.thread.isRunning}>
				<ComposerPrimitive.Send asChild>
					<TooltipIconButton
						tooltip="Send message"
						side="bottom"
						type="button"
						variant="default"
						size="icon"
						className="aui-composer-send size-8 rounded-full"
						aria-label="Send message"
					>
						<ArrowUpIcon className="aui-composer-send-icon size-4" />
					</TooltipIconButton>
				</ComposerPrimitive.Send>
			</AuiIf>
			<AuiIf condition={(s) => s.thread.isRunning}>
				<ComposerPrimitive.Cancel asChild>
					<Button
						type="button"
						variant="default"
						size="icon"
						className="aui-composer-cancel size-8 rounded-full"
						aria-label="Stop generating"
					>
						<SquareIcon className="aui-composer-cancel-icon size-3 fill-current" />
					</Button>
				</ComposerPrimitive.Cancel>
			</AuiIf>
		</div>
	);
};

const MessageError: FC = () => {
	return (
		<MessagePrimitive.Error>
			<ErrorPrimitive.Root className="aui-message-error-root mt-2 rounded-md border border-destructive bg-destructive/10 p-3 text-destructive text-sm dark:bg-destructive/5 dark:text-red-200">
				<ErrorPrimitive.Message className="aui-message-error-message line-clamp-2" />
			</ErrorPrimitive.Root>
		</MessagePrimitive.Error>
	);
};

const CollapsiblePrompt: FC<{ title: string; children: React.ReactNode }> = ({
	title,
	children,
}) => {
	const [isOpen, setIsOpen] = useState(false);
	return (
		<div className="border rounded-xl bg-accent text-accent-foreground my-2 overflow-hidden">
			<Button
				variant="ghost"
				onClick={() => setIsOpen(!isOpen)}
				aria-label={
					isOpen ? "Collapse prompt content" : "Expand prompt content"
				}
				className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold transition-colors"
			>
				<span className="flex items-center gap-2">
					<ChevronRightIcon
						className={`size-3.5 transition-transform duration-200 text-primary${isOpen && " rotate-90"}`}
					/>
					{title}
				</span>
				<span className="text-[10px] px-2 py-0.5 rounded border font-mono">
					{isOpen ? "Hide" : "Show block"}
				</span>
			</Button>
			{isOpen && (
				<div className="p-4 text-xs select-text leading-relaxed border-t max-h-[600px] overflow-y-auto custom-scrollbar">
					{children}
				</div>
			)}
		</div>
	);
};

const parsePartialStructuredOutput = (text: string): any => {
	if (!text) return null;
	const trimmed = text.trim();
	if (trimmed.startsWith("{")) {
		try {
			const parsed = parsePartialJson(trimmed, Allow.ALL);
			return parsed;
		} catch (_) {}
	}
	return null;
};

const UserMessageContent: FC = () => {
	const content = useAuiState((s) => s.message.content);

	const fullText = content
		.filter((part) => part.type === "text")
		.map((part) => (part as any).text || "")
		.join("\n");

	const partialStructuredOutput = parsePartialStructuredOutput(fullText);
	if (partialStructuredOutput) {
		return (
			<AutoScrollJsonViewer
				value={partialStructuredOutput}
				containerClassName="border p-4 mt-2 mb-2 max-h-[600px] w-full overflow-y-auto custom-scrollbar"
			/>
		);
	}

	return (
		<div className="aui-user-message-content wrap-break-word peer rounded-2xl bg-muted px-4 py-2.5 text-foreground">
			<MessagePrimitive.Parts />
		</div>
	);
};

const AssistantMessageContent: FC = () => {
	return (
		<div
			data-slot="aui_assistant-message-content"
			// [contain-intrinsic-size:auto_24px] fixes issue #4104, don't change without checking for regressions
			className="mt-2 text-foreground px-2 leading-relaxed wrap-break-word [contain-intrinsic-size:auto_24px] [content-visibility:auto]"
		>
			<MessagePrimitive.GroupedParts
				groupBy={groupPartByType({
					reasoning: ["group-chainOfThought", "group-reasoning"],
					"tool-call": ["group-chainOfThought", "group-tool"],
					"standalone-tool-call": [],
				})}
			>
				{({ part, children }) => {
					switch (part.type) {
						case "group-chainOfThought":
							return <div data-slot="aui_chain-of-thought">{children}</div>;
						case "group-reasoning": {
							const running = part.status.type === "running";
							return (
								<ReasoningGroupWrapper running={running}>
									{children}
								</ReasoningGroupWrapper>
							);
						}
						case "group-tool":
							return (
								<ToolGroupRoot>
									<ToolGroupTrigger
										count={part.indices.length}
										active={part.status.type === "running"}
									/>
									<ToolGroupContent>{children}</ToolGroupContent>
								</ToolGroupRoot>
							);
						case "text":
							return <MarkdownText />;
						case "reasoning":
							return <Reasoning {...part} />;
						case "tool-call":
							return part.toolUI ?? <ToolFallback {...part} />;
						case "indicator":
							return <LoaderIcon className="size-4 animate-spin mt-2" />;
						default:
							return null;
					}
				}}
			</MessagePrimitive.GroupedParts>
			<MessageError />
		</div>
	);
};

const ThinkingIndicator = ({
	text = "Thinking...",
	className,
}: {
	text?: string;
	className?: string;
}) => {
	return (
		<div
			className={cn(
				"flex items-center gap-2 text-muted-foreground px-2 mt-2",
				className,
			)}
		>
			<LoaderIcon className="size-4 animate-spin" />
			<span className="text-sm">{text}</span>
		</div>
	);
};

const AssistantMessage: FC = () => {
	// reserves space for action bar and compensates with `-mb` for consistent msg spacing
	// keeps hovered action bar from shifting layout (autohide doesn't support absolute positioning well)
	// for pt-[n] use -mb-[n + 6] & min-h-[n + 6] to preserve compensation
	const ACTION_BAR_PT = "pt-1.5";
	const ACTION_BAR_HEIGHT = `-mb-7.5 min-h-7.5 ${ACTION_BAR_PT}`;

	return (
		<MessagePrimitive.Root
			data-slot="aui_assistant-message-root"
			data-role="assistant"
			className="fade-in slide-in-from-bottom-1 relative animate-in duration-150 [contain-intrinsic-size:auto_300px] [content-visibility:auto]"
		>
			<div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
				<BotIcon className="size-4" />
			</div>

			<AssistantMessageContent />

			<AuiIf
				condition={(s) => s.thread.isRunning && s.message.content.length === 0}
			>
				<ThinkingIndicator />
			</AuiIf>

			<div
				data-slot="aui_assistant-message-footer"
				className={cn("ms-2 flex items-center", ACTION_BAR_HEIGHT)}
			>
				{/* <BranchPicker /> */}
				<AssistantActionBar />
			</div>
		</MessagePrimitive.Root>
	);
};

const AssistantActionBar: FC = () => {
	return (
		<ActionBarPrimitive.Root
			hideWhenRunning
			autohide="not-last"
			className="aui-assistant-action-bar-root col-start-3 row-start-2 -ms-1 flex gap-1 text-muted-foreground"
		>
			<ActionBarPrimitive.Copy asChild>
				<TooltipIconButton tooltip="Copy">
					<AuiIf condition={(s) => s.message.isCopied}>
						<CheckIcon />
					</AuiIf>
					<AuiIf condition={(s) => !s.message.isCopied}>
						<CopyIcon />
					</AuiIf>
				</TooltipIconButton>
			</ActionBarPrimitive.Copy>
			<ActionBarPrimitive.Reload asChild>
				<TooltipIconButton tooltip="Refresh">
					<RefreshCwIcon />
				</TooltipIconButton>
			</ActionBarPrimitive.Reload>
			<ActionBarMorePrimitive.Root>
				<ActionBarMorePrimitive.Trigger asChild>
					<TooltipIconButton
						tooltip="More"
						className="data-[state=open]:bg-accent"
					>
						<MoreHorizontalIcon />
					</TooltipIconButton>
				</ActionBarMorePrimitive.Trigger>
				<ActionBarMorePrimitive.Content
					side="bottom"
					align="start"
					className="aui-action-bar-more-content z-50 min-w-32 overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
				>
					<ActionBarPrimitive.ExportMarkdown asChild>
						<ActionBarMorePrimitive.Item className="aui-action-bar-more-item flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground">
							<DownloadIcon className="size-4" />
							Export as Markdown
						</ActionBarMorePrimitive.Item>
					</ActionBarPrimitive.ExportMarkdown>
				</ActionBarMorePrimitive.Content>
			</ActionBarMorePrimitive.Root>
		</ActionBarPrimitive.Root>
	);
};

const UserMessage: FC = () => {
	const content = useAuiState((s) => s.message.content);
	const fullText = content
		.filter((part) => part.type === "text")
		.map((part) => (part as any).text || "")
		.join("\n");

	const isIntermediate = isIntermediatePrompt(fullText);
	const promptTitle = getPromptTitle(fullText);

	return (
		<MessagePrimitive.Root
			data-slot="aui_user-message-root"
			className="fade-in slide-in-from-bottom-1 grid animate-in auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] content-start gap-y-2 px-2 duration-150 [contain-intrinsic-size:auto_60px] [content-visibility:auto] [&:where(>*)]:col-start-2"
			data-role="user"
		>
			<div className="col-span-full col-start-1 row-start-1 flex w-full flex-row justify-end">
				<div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
					<UserIcon className="size-4" />
				</div>
			</div>

			<UserMessageAttachments />

			<div className="aui-user-message-content-wrapper relative col-start-2 min-w-0">
				{isIntermediate ? (
					<CollapsiblePrompt title={promptTitle}>
						<UserMessageContent />
					</CollapsiblePrompt>
				) : (
					<div className="aui-user-message-content wrap-break-word peer rounded-2xl bg-muted px-4 py-2.5 text-foreground empty:hidden">
						<MessagePrimitive.Parts />
					</div>
				)}
			</div>
			<MessageError />
		</MessagePrimitive.Root>
	);
};

// const UserActionBar: FC = () => {
// 	return (
// 		<ActionBarPrimitive.Root
// 			hideWhenRunning
// 			autohide="not-last"
// 			className="aui-user-action-bar-root flex flex-col items-end"
// 		>
// 			<ActionBarPrimitive.Edit asChild>
// 				<TooltipIconButton tooltip="Edit" className="aui-user-action-edit p-4">
// 					<PencilIcon />
// 				</TooltipIconButton>
// 			</ActionBarPrimitive.Edit>
// 		</ActionBarPrimitive.Root>
// 	);
// };

const EditComposer: FC = () => {
	return (
		<MessagePrimitive.Root
			data-slot="aui_edit-composer-wrapper"
			className="flex flex-col px-2"
		>
			<ComposerPrimitive.Root className="aui-edit-composer-root ms-auto flex w-full max-w-[85%] flex-col rounded-2xl bg-muted">
				<ComposerPrimitive.Input
					className="aui-edit-composer-input min-h-14 w-full resize-none bg-transparent p-4 text-foreground text-sm outline-none"
					autoFocus
				/>
				<div className="aui-edit-composer-footer mx-3 mb-3 flex items-center gap-2 self-end">
					<ComposerPrimitive.Cancel asChild>
						<Button variant="ghost" size="sm">
							Cancel
						</Button>
					</ComposerPrimitive.Cancel>
					<ComposerPrimitive.Send asChild>
						<Button size="sm">Update</Button>
					</ComposerPrimitive.Send>
				</div>
			</ComposerPrimitive.Root>
		</MessagePrimitive.Root>
	);
};

// const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
// 	className,
// 	...rest
// }) => {
// 	return (
// 		<BranchPickerPrimitive.Root
// 			hideWhenSingleBranch
// 			className={cn(
// 				"aui-branch-picker-root -ms-2 me-2 inline-flex items-center text-muted-foreground text-xs",
// 				className,
// 			)}
// 			{...rest}
// 		>
// 			<BranchPickerPrimitive.Previous asChild>
// 				<TooltipIconButton tooltip="Previous">
// 					<ChevronLeftIcon />
// 				</TooltipIconButton>
// 			</BranchPickerPrimitive.Previous>
// 			<span className="aui-branch-picker-state font-medium">
// 				<BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
// 			</span>
// 			<BranchPickerPrimitive.Next asChild>
// 				<TooltipIconButton tooltip="Next">
// 					<ChevronRightIcon />
// 				</TooltipIconButton>
// 			</BranchPickerPrimitive.Next>
// 		</BranchPickerPrimitive.Root>
// 	);
// };

const ReasoningGroupWrapper: FC<{
	running: boolean;
	children: React.ReactNode;
}> = ({ running, children }) => {
	const [elapsed, setElapsed] = useState(0);

	useEffect(() => {
		if (!running) {
			setElapsed(0);
			return;
		}

		const start = Date.now();
		const interval = setInterval(() => {
			setElapsed(Math.round((Date.now() - start) / 1000));
		}, 500);

		return () => clearInterval(interval);
	}, [running]);

	return (
		<ReasoningRoot defaultOpen={running}>
			<ReasoningTrigger
				active={running}
				duration={elapsed > 0 ? elapsed : undefined}
			/>
			<ReasoningContent aria-busy={running}>
				<ReasoningText>{children}</ReasoningText>
			</ReasoningContent>
		</ReasoningRoot>
	);
};
