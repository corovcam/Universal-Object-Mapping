import { Bug } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Empty,
	EmptyContent,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

export function SpinnerEmpty({
	title,
	description,
	className,
}: {
	title: string;
	description: string;
	className?: string;
}) {
	return (
		<Empty
			className={cn("w-full bg-card text-card-foreground size-full", className)}
		>
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

export function ErrorEmpty({
	title,
	description,
	onClick,
	className,
}: {
	title: string;
	description: string;
	onClick: () => void;
	className?: string;
}) {
	return (
		<Empty
			className={cn("w-full bg-card text-destructive size-full", className)}
		>
			<EmptyHeader>
				<EmptyMedia variant="icon" className="bg-transparent">
					<Bug className="size-10 text-destructive/90" />
				</EmptyMedia>
				<EmptyTitle>{title}</EmptyTitle>
				<EmptyDescription className="text-destructive/90">
					{description}
				</EmptyDescription>
				<EmptyContent className="text-primary">
					<Button
						variant="outline"
						size="sm"
						onClick={onClick}
						className="mt-2"
					>
						Reload
					</Button>
				</EmptyContent>
			</EmptyHeader>
		</Empty>
	);
}
