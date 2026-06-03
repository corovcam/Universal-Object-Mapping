import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";

export function SpinnerEmpty({
	title,
	description,
}: {
	title: string;
	description: string;
}) {
	return (
		<Empty className="w-full">
			<EmptyHeader>
				<EmptyMedia variant="icon" className="bg-transparent">
					<Spinner className="size-10" />
				</EmptyMedia>
				<EmptyTitle>{title}</EmptyTitle>
				<EmptyDescription>{description}</EmptyDescription>
			</EmptyHeader>
		</Empty>
	);
}
