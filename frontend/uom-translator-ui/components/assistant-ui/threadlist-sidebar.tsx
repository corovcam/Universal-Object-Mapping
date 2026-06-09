"use-client";

import { BookOpen, Settings } from "lucide-react";
import Image from "next/image";
import { useTheme } from "next-themes";
import type * as React from "react";
import { useEffect, useState } from "react";
import { ThreadList } from "@/components/assistant-ui/thread-list";
import { ThemeToggle } from "@/components/buttons";
import { GitHubIcon } from "@/components/icons/github";
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarRail,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfigModal } from "../config-modal";
import { IdeLink } from "../ide-link";
import ComponentErrorBoundary from "@/app/component-error-boundary";

export function ThreadListSidebar({
	...props
}: React.ComponentProps<typeof Sidebar>) {
	const [isConfigOpen, setIsConfigOpen] = useState(false);
	const { theme } = useTheme();
	const [isClient, setIsClient] = useState(false);

	useEffect(() => {
		setIsClient(true);
	}, []);

	useEffect(() => {
		if (typeof window !== "undefined") {
			const is_onboarded = localStorage.getItem("uom_config_onboarded");
			setIsConfigOpen(is_onboarded === null || is_onboarded !== "true");
		}
	}, []);

	return (
		<Sidebar {...props}>
			<SidebarHeader className="aui-sidebar-header mb-2 border-b">
				<div className="aui-sidebar-header-content flex items-center justify-between">
					<SidebarMenu>
						<SidebarMenuItem>
							<SidebarMenuButton size="lg" asChild tooltip="UOM Assistant Home">
								<a href="/" aria-label="UOM Assistant Home">
									{/* <div className="aui-sidebar-header-icon-wrapper bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg shimemer-bg shimmer-color-indigo-100 shimmer-spread-200 shimmer-angle-75">
										<FolderGit className="aui-sidebar-header-icon size-5" />
									</div> */}
									<div className="aspect-square size-8">
										{isClient ? (
											theme === "light" ? (
												<Image
													src="/logo-uom-black-730.svg"
													alt="UOM Logo Black"
													width={32}
													height={32}
												/>
											) : (
												<Image
													src="/logo-uom-white-730.svg"
													alt="UOM Logo White"
													width={32}
													height={32}
												/>
											)
										) : (
											<Skeleton className="size-full" />
										)}
									</div>
									<div className="aui-sidebar-header-heading me-6 flex flex-col gap-0.5 leading-none">
										<span className="aui-sidebar-header-title font-semibold">
											UOM Assistant
										</span>
									</div>
								</a>
							</SidebarMenuButton>
						</SidebarMenuItem>
					</SidebarMenu>
				</div>
			</SidebarHeader>
			<SidebarContent className="aui-sidebar-content px-2">
				<ThreadList />
			</SidebarContent>
			<SidebarGroup className="aui-sidebar-group border-t mt-auto">
				<SidebarGroupLabel>Connect your IDE</SidebarGroupLabel>
				<SidebarGroupContent>
					<ComponentErrorBoundary title="An error occurred while loading the IDE integration.">
						<IdeLink />
					</ComponentErrorBoundary>
					{/* <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton>
                  Select Workspace
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-[--radix-popper-anchor-width]">
                <DropdownMenuItem>
                  <span>Acme Inc</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem> */}
				</SidebarGroupContent>
			</SidebarGroup>
			<SidebarGroup className="aui-sidebar-group border-t">
				<SidebarGroupLabel>Configuration</SidebarGroupLabel>
				<SidebarGroupContent>
					<SidebarMenuButton
						onClick={() => setIsConfigOpen(true)}
						className="h-9 justify-start gap-2 rounded-lg px-3 text-sm"
						tooltip="Open Settings"
					>
						<Settings className="aui-sidebar-footer-icon size-4" />
						Settings
					</SidebarMenuButton>
					<ThemeToggle
						Component={SidebarMenuButton}
						className="h-9 justify-start gap-2 rounded-lg px-3 text-sm"
						tooltip="Toggle Theme"
					/>
				</SidebarGroupContent>
			</SidebarGroup>
			<SidebarFooter className="aui-sidebar-footer border-t">
				<SidebarGroupLabel>Links</SidebarGroupLabel>
				<SidebarMenu>
					<SidebarMenuItem>
						<SidebarMenuButton
							asChild
							className="rounded-lg px-3 text-sm"
							tooltip="Open Documentation"
						>
							<a
								href="https://github.com/corovcam/Universal-Object-Mapping"
								target="_blank"
								rel="noopener noreferrer"
								aria-label="Open Documentation"
							>
								<BookOpen className="aui-sidebar-footer-icon size-4" />
								Docs
							</a>
						</SidebarMenuButton>
					</SidebarMenuItem>
					<SidebarMenuItem>
						<SidebarMenuButton
							asChild
							className="rounded-lg px-3 text-sm"
							tooltip="View on GitHub"
						>
							<a
								href="https://github.com/corovcam/Universal-Object-Mapping"
								target="_blank"
								rel="noopener noreferrer"
								aria-label="View on GitHub"
							>
								<GitHubIcon className="aui-sidebar-footer-icon size-4" />
								GitHub
							</a>
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarFooter>
			<SidebarRail />
			<ConfigModal
				isOpen={isConfigOpen}
				onClose={() => setIsConfigOpen(false)}
				onSave={() => setIsConfigOpen(false)}
			/>
		</Sidebar>
	);
}
