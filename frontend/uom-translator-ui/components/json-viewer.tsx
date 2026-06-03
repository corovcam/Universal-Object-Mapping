"use client";

import type { JsonViewProps } from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";
import { githubLightTheme } from "@uiw/react-json-view/githubLight";
import dynamic from "next/dynamic";
import { Suspense } from "react";
import { useTheme } from "@/components/theme-provider";
import { SkeletonText } from "@/components/ui/skeleton";

const JsonView = dynamic(() => import("@uiw/react-json-view"), { ssr: false });

export function JsonViewer({ value, ...props }: JsonViewProps<object>) {
	const { theme } = useTheme();

	return (
		<Suspense fallback={<SkeletonText count={4} className="h-48 w-full" />}>
			<JsonView
				value={value}
				style={theme === "dark" ? githubDarkTheme : githubLightTheme}
				collapsed={2}
			/>
		</Suspense>
	);
}
