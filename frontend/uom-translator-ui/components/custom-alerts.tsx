import { AlertTriangle, Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// export const CustomAlert = ({
//   title,
//   description,
//   Icon,
//   variant = "info",
// }: {
//   title: string;
//   description: string | React.ReactNode;
//   Icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
//   variant?: "info" | "warning";
// }) => {
//   const alertStyles =
//     variant === "warning"
//       ? "gap-3 border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-50"
//       : "gap-3 border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-50";

//   const DefaultIcon = variant === "warning" ? AlertTriangle : Info;

//   return (
//     <Alert className={alertStyles}>
//       {(Icon || DefaultIcon) && (
//         <div className="size-4 shrink-0">
//           {Icon ? <Icon className="size-full" /> : <DefaultIcon className="size-full" />}
//         </div>
//       )}
//       <div>
//         <AlertTitle>{title}</AlertTitle>
//         <AlertDescription>{description}</AlertDescription>
//       </div>
//     </Alert>
//   );
// };

export const InfoAlert = ({
	title,
	description,
	Icon = Info,
}: {
	title: string;
	description: string | React.ReactNode;
	Icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
}) => {
	return (
		<Alert className="gap-3 border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-50">
			<Icon className="size-4 shrink-0" />
			<div>
				<AlertTitle>{title}</AlertTitle>
				<AlertDescription>{description}</AlertDescription>
			</div>
		</Alert>
	);
};

export const WarningAlert = ({
	title,
	description,
	Icon = AlertTriangle,
}: {
	title: string;
	description: string | React.ReactNode;
	Icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
}) => {
	return <InfoAlert title={title} description={description} Icon={Icon} />;
};
