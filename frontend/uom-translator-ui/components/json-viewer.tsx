"use client";

import type { JsonViewProps } from "@uiw/react-json-view";
import JsonView from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";
import { githubLightTheme } from "@uiw/react-json-view/githubLight";
import { useTheme } from "next-themes";
import { Suspense, useEffect, useRef, useState } from "react";
import { SkeletonText } from "@/components/ui/skeleton";

/**
 * React Component that visualizes objects as formatted, interactive JSON trees.
 * Automatically supports light and dark themes using next-themes.
 * Incorporates custom string node formatting to preserve line breaks and white spaces.
 *
 * @param {JsonViewProps<object>} props - Props passed down to the underlying `@uiw/react-json-view` component.
 * @returns {React.JSX.Element} Interactive JSON tree element.
 */
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
					render={({ children, ...reset }, { type }) => {
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

/**
 * Prop types for the AutoScrollJsonViewer component.
 */
interface AutoScrollJsonViewerProps
	extends Omit<JsonViewProps<object>, "value"> {
	/** JSON value or object payload to render. */
	value: unknown;
	/** Optional tailwind CSS wrapper container class name. */
	containerClassName?: string;
}

/**
 * Enhanced JSON tree viewer wrapper that handles automatic scroll locking.
 * Keeps the scroll position pinned to the bottom of the container while JSON is streaming,
 * unless the user manually scrolls upwards to view historical lines.
 *
 * @param {AutoScrollJsonViewerProps} props - Component properties.
 * @returns {React.JSX.Element} Scroll-aware container wrapping the JSON tree.
 */
export function AutoScrollJsonViewer({
	value,
	containerClassName,
	...props
}: AutoScrollJsonViewerProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const [isPinned, setIsPinned] = useState(true);
	const isPinnedRef = useRef(true);

	useEffect(() => {
		isPinnedRef.current = isPinned;
	}, [isPinned]);

	useEffect(() => {
		const container = containerRef.current;
		if (!container) return;

		const observer = new MutationObserver(() => {
			if (isPinnedRef.current) {
				container.scrollTop = container.scrollHeight - container.clientHeight;
			}
		});

		observer.observe(container, {
			childList: true,
			subtree: true,
			characterData: true,
		});

		return () => observer.disconnect();
	}, []);

	useEffect(() => {
		const container = containerRef.current;
		if (!container || value === undefined) return;
		if (isPinnedRef.current) {
			container.scrollTop = container.scrollHeight - container.clientHeight;
		}
	}, [value]);

	const handleScroll = () => {
		const container = containerRef.current;
		if (!container) return;
		const { scrollTop, scrollHeight, clientHeight } = container;
		const isAtBottom = scrollHeight - clientHeight - scrollTop < 15;
		if (isPinnedRef.current !== isAtBottom) {
			setIsPinned(isAtBottom);
		}
	};

	return (
		<div
			ref={containerRef}
			className={containerClassName}
			onScroll={handleScroll}
		>
			<JsonViewer value={value as object} {...props} />
		</div>
	);
}
