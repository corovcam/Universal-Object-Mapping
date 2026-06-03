import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
	return (
		<div
			data-slot="skeleton"
			className={cn("animate-pulse rounded-md bg-accent", className)}
			{...props}
		/>
	);
}

export function SkeletonText({
	count,
	className,
	...props
}: { count: number } & React.ComponentProps<"div">) {
	return (
		<div
			className={cn("flex w-full max-w-xs flex-col gap-2", className)}
			{...props}
		>
			{Array.from({ length: count }).map((_, i) => (
				<Skeleton key={i} className="h-4 w-full" />
			))}
		</div>
	);
}

export function SkeletonCard({
	count,
	className,
	...props
}: { count: number } & React.ComponentProps<typeof Card>) {
	return (
		<Card className={cn("w-full max-w-xs", className)} {...props}>
			<CardHeader>
				{Array.from({ length: count }).map((_, i) => (
					<Skeleton key={i} className="h-4 w-full" />
				))}
			</CardHeader>
			<CardContent>
				<Skeleton className="aspect-video w-full" />
			</CardContent>
		</Card>
	);
}

export { Skeleton };
