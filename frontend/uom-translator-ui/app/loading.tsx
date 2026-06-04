import { SpinnerEmpty } from "@/components/spinner-empty";

export default function Loading() {
	return (
		<div className="flex h-dvh w-full items-center justify-center">
			<SpinnerEmpty
				title="Loading..."
				description="Please wait while we load the assistant."
			/>
		</div>
	);
}
