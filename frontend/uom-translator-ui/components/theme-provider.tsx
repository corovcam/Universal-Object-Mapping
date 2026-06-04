"use client";

import { Moon, Sun } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import type { SidebarMenuButton } from "@/components/ui/sidebar";

type Theme = "light" | "dark" | "system";

type ThemeContextValue = {
	theme: Theme;
	resolvedTheme: "light" | "dark";
	setTheme: (theme: Theme) => void;
	toggleTheme: () => void;
};

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

function getSystemTheme(): "light" | "dark" {
	if (typeof window === "undefined") return "light";
	return window.matchMedia("(prefers-color-scheme: dark)").matches
		? "dark"
		: "light";
}

function applyTheme(theme: Theme) {
	const resolvedTheme = theme === "system" ? getSystemTheme() : theme;
	document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
	localStorage.setItem("theme", theme);
}

export function ThemeProvider({
	children,
	defaultTheme = "system",
}: {
	children: React.ReactNode;
	defaultTheme?: Theme;
}) {
	const [theme, setThemeState] = React.useState<Theme>(defaultTheme);
	const [mounted, setMounted] = React.useState(false);

	React.useEffect(() => {
		const stored =
			(localStorage.getItem("theme") as Theme | null) ?? defaultTheme;
		setThemeState(stored);
		setMounted(true);
	}, [defaultTheme]);

	React.useEffect(() => {
		if (!mounted) return;
		applyTheme(theme);
	}, [theme, mounted]);

	React.useEffect(() => {
		if (theme !== "system") return;

		const media = window.matchMedia("(prefers-color-scheme: dark)");
		const listener = () => applyTheme("system");

		media.addEventListener("change", listener);
		return () => media.removeEventListener("change", listener);
	}, [theme]);

	const value = React.useMemo<ThemeContextValue>(() => {
		const resolvedTheme = theme === "system" ? getSystemTheme() : theme;

		return {
			theme,
			resolvedTheme,
			setTheme: (nextTheme: Theme) => setThemeState(nextTheme),
			toggleTheme: () =>
				setThemeState((current) => (current === "dark" ? "light" : "dark")),
		};
	}, [theme]);

	if (!mounted) {
		return <>{children}</>;
	}

	return (
		<ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
	);
}

export function useTheme() {
	const ctx = React.useContext(ThemeContext);
	if (!ctx) {
		return {
			theme: "dark" as const,
			resolvedTheme: "dark" as const,
			setTheme: () => {},
			toggleTheme: () => {},
		};
	}
	return ctx;
}

export function ThemeToggle({
	Component = Button,
	...props
}: {
	Component?: React.ElementType;
} & React.ComponentProps<typeof Button | typeof SidebarMenuButton | "button">) {
	const { theme, toggleTheme } = useTheme();

	const Comp = Component || Button;

	return (
		<Comp
			onClick={toggleTheme}
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
	);
}
