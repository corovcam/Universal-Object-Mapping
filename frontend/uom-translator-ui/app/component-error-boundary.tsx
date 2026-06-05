"use client";
import { unstable_catchError as catchError, type ErrorInfo } from "next/error";

import { ErrorEmpty } from "@/components/custom-empty";

function ComponentErrorBoundary(
	props: { title: string },
	{ error, unstable_retry }: ErrorInfo,
) {
	return (
		<div className="flex h-dvh w-full items-center justify-center">
			<ErrorEmpty
				title={props.title}
				description={error?.message}
				onClick={unstable_retry}
			/>
		</div>
	);
}

export default catchError(ComponentErrorBoundary);
