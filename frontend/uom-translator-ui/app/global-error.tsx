"use client";

import { ErrorEmpty } from "@/components/custom-empty";

export default function GlobalError({
	error,
	unstable_retry,
}: {
	error: Error & { digest?: string };
	unstable_retry: () => void;
}) {
	return (
		<html lang="en">
			<body>
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
