"use-client";

import { ThreadList } from "@/components/assistant-ui/thread-list";
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
import { BookOpen, FolderGit, Settings } from "lucide-react";
import type * as React from "react";
import { useEffect, useState } from "react";
import { ConfigModal } from "../config-modal";
import { IdeLink } from "../ide-link";

export function ThreadListSidebar({
	...props
}: React.ComponentProps<typeof Sidebar>) {
	const [isConfigOpen, setIsConfigOpen] = useState(false);

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
							<SidebarMenuButton size="lg" asChild>
								<a
									href="https://assistant-ui.com"
									target="_blank"
									rel="noopener noreferrer"
								>
									<div className="aui-sidebar-header-icon-wrapper bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
										<FolderGit className="aui-sidebar-header-icon size-5" />
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
			<SidebarRail />
			<SidebarGroup className="aui-sidebar-group border-t mt-auto">
				<SidebarGroupLabel>Connect your IDE</SidebarGroupLabel>
				<SidebarGroupContent>
					<IdeLink />
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
						className="aui-thread-list-new h-9 justify-start gap-2 rounded-lg px-3 text-sm"
					>
						<Settings className="aui-sidebar-footer-icon size-4" />
						Settings
					</SidebarMenuButton>
				</SidebarGroupContent>
			</SidebarGroup>
			<SidebarFooter className="aui-sidebar-footer border-t">
				<SidebarGroupLabel>Links</SidebarGroupLabel>
				<SidebarMenu>
					<SidebarMenuItem>
						<SidebarMenuButton asChild className="rounded-lg px-3 text-sm">
							<a
								href="https://github.com/corovcam/Universal-Object-Mapping"
								target="_blank"
								rel="noopener noreferrer"
							>
								<div className="text-sidebar-primary-foreground flex aspect-square items-center justify-center">
									<BookOpen className="aui-sidebar-footer-icon size-4" />
								</div>
								<span className="aui-sidebar-footer-title font-semibold">
									Docs
								</span>
							</a>
						</SidebarMenuButton>
					</SidebarMenuItem>
					<SidebarMenuItem>
						<SidebarMenuButton asChild className="rounded-lg px-3 text-sm">
							<a
								href="https://github.com/corovcam/Universal-Object-Mapping"
								target="_blank"
								rel="noopener noreferrer"
							>
								<div className="text-sidebar-primary-foreground flex aspect-square items-center justify-center">
									<GitHubIcon className="aui-sidebar-footer-icon size-4" />
								</div>
								<span className="aui-sidebar-footer-title font-semibold">
									GitHub
								</span>
							</a>
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarFooter>
			<ConfigModal
				isOpen={isConfigOpen}
				onClose={() => setIsConfigOpen(false)}
				onSave={() => setIsConfigOpen(false)}
			/>
		</Sidebar>
	);
}
