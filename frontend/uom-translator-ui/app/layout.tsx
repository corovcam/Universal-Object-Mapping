import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import "streamdown/styles.css";
import "./globals.css";

const geistSans = Geist({
	variable: "--font-geist-sans",
	subsets: ["latin"],
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
});

export const metadata: Metadata = {
	title: "Universal Object Mapping (UOM) Translator",
	description:
		"Advanced paradigm migrator translating C# Entity Framework relational schemas and queries to Java Spring Data MongoDB/Neo4j NoSQL schemas and queries.",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html
			lang="en"
			className="dark"
			style={{ colorScheme: "dark" }}
			suppressHydrationWarning
		>
			<body
				className={`${geistSans.variable} ${geistMono.variable} antialiased bg-slate-950 text-slate-100`}
				suppressHydrationWarning
			>
				<ThemeProvider defaultTheme="dark">
					<TooltipProvider>{children}</TooltipProvider>
				</ThemeProvider>
			</body>
		</html>
	);
}
