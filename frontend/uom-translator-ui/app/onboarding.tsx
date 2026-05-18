"use client";

import { HelpCircleIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

export function OnboardingModal() {
	return (
		<Dialog>
			<DialogTrigger asChild>
				<Button variant="ghost" size="icon" className="rounded-full">
					<HelpCircleIcon className="w-5 h-5" />
					<span className="sr-only">Help / Onboarding</span>
				</Button>
			</DialogTrigger>
			<DialogContent className="sm:max-w-xl">
				<DialogHeader>
					<DialogTitle>Welcome to Universal Object Mapping (UOM)</DialogTitle>
					<DialogDescription>
						An LLM-based iterative translation architecture.
					</DialogDescription>
				</DialogHeader>
				<div className="flex flex-col gap-4 py-4 text-sm text-foreground">
					<p>
						<strong>What is this?</strong>
						<br />
						This UI connects to a LangGraph Orchestrator that translates
						database schemas and queries across different ORM/ODM/OGM paradigms
						(e.g., Relational .NET EF Core to Graph Java Spring Data Neo4j).
					</p>
					<p>
						<strong>How to use:</strong>
						<br />
						1. Use the left pane to specify your source and target frameworks.
						<br />
						2. Provide the source schema and/or query code.
						<br />
						3. Click "Start Translation".
						<br />
						4. The orchestrator will automatically generate, compile, and
						validate the code, checking for equivalence.
						<br />
						5. If validation fails, it loops up to 3 times to correct the code
						automatically.
					</p>
					<p>
						<strong>Human in the loop:</strong>
						<br />
						If the orchestrator is unable to resolve failures after 3 attempts,
						it will pause. You will be prompted to provide manual intervention
						or correction instructions before resuming.
					</p>
				</div>
			</DialogContent>
		</Dialog>
	);
}
