"use client";

import { SettingsIcon } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

export function SettingsModal() {
	const [model, setModel] = useState("einfra/kimi-k2.6");
	const [apiKey, setApiKey] = useState("");
	const [dbUri, setDbUri] = useState("mongodb://localhost:27027");

	return (
		<Dialog>
			<DialogTrigger asChild>
				<Button variant="ghost" size="icon" className="rounded-full">
					<SettingsIcon className="w-5 h-5" />
					<span className="sr-only">Settings</span>
				</Button>
			</DialogTrigger>
			<DialogContent className="sm:max-w-xl">
				<DialogHeader>
					<DialogTitle>Configuration</DialogTitle>
					<DialogDescription>
						Edit the configurable context defined in the LangGraph Orchestrator.
					</DialogDescription>
				</DialogHeader>
				<div className="flex flex-col gap-4 py-4">
					<div className="flex flex-col gap-1.5 text-sm">
						<label htmlFor="model" className="font-medium">
							Model
						</label>
						<input
							id="model"
							type="text"
							value={model}
							onChange={(e) => setModel(e.target.value)}
							className="border rounded-md px-3 py-2 bg-background"
						/>
					</div>
					<div className="flex flex-col gap-1.5 text-sm">
						<label htmlFor="apiKey" className="font-medium">
							OpenAI API Key
						</label>
						<input
							id="apiKey"
							type="password"
							value={apiKey}
							onChange={(e) => setApiKey(e.target.value)}
							className="border rounded-md px-3 py-2 bg-background"
							placeholder="sk-..."
						/>
					</div>
					<div className="flex flex-col gap-1.5 text-sm">
						<label htmlFor="dbUri" className="font-medium">
							MongoDB URI
						</label>
						<input
							id="dbUri"
							type="text"
							value={dbUri}
							onChange={(e) => setDbUri(e.target.value)}
							className="border rounded-md px-3 py-2 bg-background"
						/>
					</div>
					<div className="flex flex-col gap-1.5 text-sm">
						<label className="font-medium">Orchestrator URLs</label>
						<p className="text-xs text-muted-foreground">
							Other URIs (DB Toolbox, Services) can be configured via
							environment variables.
						</p>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
