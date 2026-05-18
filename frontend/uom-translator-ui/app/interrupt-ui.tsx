"use client";

import {
	useLangGraphInterruptState,
	useLangGraphSendCommand,
} from "@assistant-ui/react-langgraph";
import { Button } from "@/components/ui/button";

export function LangGraphInterrupt() {
	const interrupt = useLangGraphInterruptState();
	const sendCommand = useLangGraphSendCommand();

	if (!interrupt) return null;

	return (
		<div className="absolute inset-x-0 top-0 z-50 bg-destructive/10 border-b border-destructive p-4 flex flex-col gap-2 backdrop-blur-sm">
			<div className="flex items-start justify-between">
				<div>
					<h3 className="font-semibold text-destructive">
						Human Intervention Required
					</h3>
					<p className="text-sm text-foreground mt-1">
						The orchestrator has exhausted its automatic retry limit (3 loops).
						Please review the chat history and validation failures below. You
						can send a message with manual corrections or instructions, then
						click Resume to continue.
					</p>
				</div>
			</div>
			<div className="flex gap-2 justify-end mt-2">
				<Button
					variant="default"
					onClick={() => sendCommand({ resume: "continue" })}
				>
					Resume Orchestrator
				</Button>
			</div>
		</div>
	);
}
