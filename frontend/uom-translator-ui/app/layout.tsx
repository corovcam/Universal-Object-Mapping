import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import "streamdown/styles.css";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
	variable: "--font-geist-sans",
	subsets: ["latin"],
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
});

export const metadata: Metadata = {
	title: "Universal Object Mapping Assistant",
	description:
		"Advanced paradigm migrator translating C# Entity Framework relational schemas and queries to Java Spring Data MongoDB/Neo4j NoSQL schemas and queries.",
	authors: [
		{
			name: "Martin Čorovčák",
			url: "https://github.com/corovcam",
		},
	],
	creator: "Martin Čorovčák",
	openGraph: {
		title: "Universal Object Mapping Assistant",
		description:
			"Advanced paradigm migrator translating C# Entity Framework relational schemas and queries to Java Spring Data MongoDB/Neo4j NoSQL schemas and queries.",
		siteName: "Universal Object Mapping Assistant",
	},
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" suppressHydrationWarning>
			<body
				className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
				suppressHydrationWarning
			>
				<ThemeProvider
					defaultTheme="dark"
					attribute="class"
					enableSystem
					disableTransitionOnChange
				>
					<TooltipProvider>{children}</TooltipProvider>
					<Toaster position="top-center" />
				</ThemeProvider>
			</body>
		</html>
	);
}
