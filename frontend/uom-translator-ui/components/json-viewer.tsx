"use client";

import type { JsonViewProps } from "@uiw/react-json-view";
import JsonView from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";
import { githubLightTheme } from "@uiw/react-json-view/githubLight";
import dynamic from "next/dynamic";
import { Suspense } from "react";
import { useTheme } from "@/components/theme-provider";
import { SkeletonText } from "@/components/ui/skeleton";

// const JsonView = dynamic(() => import("@uiw/react-json-view"), { ssr: false });

export function JsonViewer({ value, ...props }: JsonViewProps<object>) {
	const { theme } = useTheme();

	// TODO: Preprocess the JSON: each string value that contains a newline character will be rendered with preserved whitespace and line breaks.
	// if (typeof value === "object" && value !== null) {
	// 	for (const key in value) {
	// 		if (typeof value[key] === "string" && value[key].includes("\n")) {
	// 			value[key] = value[key].replace(/\n/g, "\\n");
	// 		}
	// 	}
	// }

	return (
		<Suspense fallback={<SkeletonText count={4} className="h-48 w-full" />}>
			<JsonView
				value={value}
				style={theme === "dark" ? githubDarkTheme : githubLightTheme}
				collapsed={2}
				shortenTextAfterLength={100}
				{...props}
			>
				<JsonView.String
					render={({ children, ...reset }, { type, value, keyName }) => {
						if (type === "type") {
							return <span {...reset} />;
						}
						try {
							const stringNode = children as string;
							if (type === "value" && stringNode.includes("\n")) {
								return (
									<span
										{...reset}
										className="whitespace-pre-wrap wrap-break-word"
									>
										"{children}"
									</span>
								);
							}
						} catch {
							// If any error occurs during rendering, fall back to default rendering
						}
					}}
				/>
			</JsonView>
		</Suspense>
	);
}
