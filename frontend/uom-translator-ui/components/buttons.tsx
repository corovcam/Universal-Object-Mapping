"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import type { SidebarMenuButton } from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";

export const ThemeToggle = ({
	Component = Button,
	...props
}: {
	Component?: React.ElementType;
} & React.ComponentProps<
	typeof Button | typeof SidebarMenuButton | "button"
>) => {
	const { theme, setTheme } = useTheme();
	const [isClient, setIsClient] = useState(false);

	useEffect(() => {
		setIsClient(true);
	}, []);

	const Comp = Component || Button;

	return isClient ? (
		<Comp
			onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
			className="rounded-lg px-3 text-sm border-zinc-200 bg-white text-zinc-900 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100"
			aria-label={
				theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"
			}
			tooltip={
				theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"
			}
			{...props}
		>
			{theme === "dark" ? (
				<>
					<Sun className="size-4" />
					Light mode
				</>
			) : (
				<>
					<Moon className="size-4" />
					Dark mode
				</>
			)}
		</Comp>
	) : (
		<Skeleton className="h-9 w-full" />
	);
};
