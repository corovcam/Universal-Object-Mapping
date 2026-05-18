"use client";

import { useAuiState } from "@assistant-ui/react";
import { ClockIcon } from "lucide-react";
import { useEffect, useState } from "react";

export function RequestTimer() {
	const isRunning = useAuiState((s) => s.thread.isRunning);
	const [elapsed, setElapsed] = useState(0);

	useEffect(() => {
		let interval: NodeJS.Timeout;
		if (isRunning) {
			interval = setInterval(() => {
				setElapsed((prev) => prev + 1);
			}, 1000);
		} else {
			setElapsed(0);
		}

		return () => clearInterval(interval);
	}, [isRunning]);

	if (!isRunning && elapsed === 0) return null;

	return (
		<div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded-md">
			<ClockIcon className="w-3.5 h-3.5" />
			<span>{elapsed}s</span>
		</div>
	);
}
