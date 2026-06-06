"use client";

import { Geist, Geist_Mono } from "next/font/google";
import { ErrorEmpty } from "@/components/custom-empty";

const geistSans = Geist({
	variable: "--font-geist-sans",
	subsets: ["latin"],
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
});

export default function GlobalError({
	error,
	unstable_retry,
}: {
	error: Error & { digest?: string };
	unstable_retry: () => void;
}) {
	return (
		<html lang="en" className="dark" style={{ colorScheme: "dark" }}>
			<body
				className={`${geistSans.variable} ${geistMono.variable} antialiased bg-slate-950 text-slate-100`}
			>
				<div className="flex h-dvh w-full items-center justify-center">
					<ErrorEmpty
						title="An error occurred"
						description={error?.message}
						onClick={unstable_retry}
					/>
				</div>
			</body>
		</html>
	);
}
