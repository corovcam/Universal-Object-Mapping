"use client";

import {
	Check,
	ChevronRight,
	Code2,
	Copy,
	ExternalLink,
	RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useGraphStateContext } from "@/hooks/use-graph-state-context";
import { FrameworkType, LanguageType } from "@/lib/types";
import { getFrameworkTypeByName } from "@/lib/utils";

/**
 * Supported IDE protocols that can hook into remote sandboxes.
 */
export enum SupportedIDEs {
	/** Visual Studio Code (vscode:// scheme) */
	vscode = "vscode",
	/** Cursor AI Editor (cursor:// scheme) */
	cursor = "cursor",
	/** JetBrains Gateway client (jetbrains-gateway:// scheme) */
	jetbrains = "jetbrains",
}

/**
 * Sandbox authentication details and SSH endpoints retrieved from Daytona client API.
 */
export interface SandboxInfo {
	/** Active compilation framework (e.g. dotnet_efcore, java_spring_data_mongodb). */
	framework: FrameworkType | null;
	/** Container instance ID allocated by Daytona. */
	sandboxId: string;
	/** Standard SSH connection command. */
	sshCommand: string;
	/** Ephemeral API token for connection handshake. */
	token: string;
}

/**
 * React Component providing deep links and SSH credentials for IDEs.
 * Enables developers to connect VS Code, Cursor, or JetBrains Gateway directly into
 * the Daytona container compilation sandboxes in order to examine build environments or debug code.
 *
 * @returns {React.JSX.Element} Remote workspace linking controls.
 */
export function IdeLink() {
	const { graphState } = useGraphStateContext();

	const [copied, setCopied] = useState(false);
	const [activeIde, setActiveIde] = useState<SupportedIDEs>(
		SupportedIDEs.vscode,
	);
	const [showDropdown, setShowDropdown] = useState(false);

	const [activePlatform, setActivePlatform] = useState<LanguageType>(
		LanguageType.JAVA,
	);
	const [loading, setLoading] = useState(false);
	const [sandboxInfo, setSandboxInfo] = useState<SandboxInfo | null>(null);

	const containerRef = useRef<HTMLDivElement>(null);

	const sourceFramework = graphState?.source_target
		? getFrameworkTypeByName(graphState.source_target)
		: FrameworkType.DOTNET_EFCORE;
	const destFramework = graphState?.destination_target
		? getFrameworkTypeByName(graphState.destination_target)
		: FrameworkType.JAVA_SPRING_DATA_MONGODB;
	const activeFramework =
		activePlatform === LanguageType.DOTNET ? sourceFramework : destFramework;

	/**
	 * Fetches the active workspace container references and SSH credentials from the LangGraph dev server.
	 * Dispatches requests to `/sandboxes/framework/[framework]` and `/sandbox/[id]/ssh-token` endpoints.
	 */
	const fetchSandboxSsh = useCallback(async () => {
		setLoading(true);
		try {
			const apiUrl =
				process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:2024";

			const sandboxRes = await fetch(
				`${apiUrl}/sandboxes/framework/${activeFramework}`,
			);
			if (!sandboxRes.ok)
				throw new Error(
					`Failed to fetch sandbox: ${sandboxRes.status} ${sandboxRes.statusText} ${await sandboxRes.text()}`,
				);
			const sandboxData = await sandboxRes.json();
			console.log(sandboxData);

			const tokenRes = await fetch(
				`${apiUrl}/sandbox/${sandboxData.id}/ssh-token`,
				{ method: "POST" },
			);
			if (!tokenRes.ok)
				throw new Error(
					`Failed to create SSH token: ${tokenRes.status} ${tokenRes.statusText} ${await tokenRes.text()}`,
				);
			const tokenData = await tokenRes.json();
			console.log(tokenData);

			setSandboxInfo({
				framework: activeFramework,
				sandboxId: sandboxData.id,
				sshCommand: tokenData.ssh_command,
				token: tokenData.token,
			});
		} catch (err) {
			console.error("Failed fetching sandbox SSH credentials from API", err);
			setSandboxInfo(null);
		} finally {
			setLoading(false);
		}
	}, [activeFramework]);

	useEffect(() => {
		fetchSandboxSsh();
	}, [fetchSandboxSsh]);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (
				containerRef.current &&
				!containerRef.current.contains(event.target as Node)
			) {
				setShowDropdown(false);
			}
		};
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, []);

	/**
	 * RegEx parser utility to extract the user, host, and port components from a raw SSH command string.
	 *
	 * @param {string} [cmd] - Raw SSH command (e.g. "ssh -p 2222 root@127.0.0.1").
	 * @param {string} [token] - Handshake access token.
	 * @returns {{ user: string | null, host: string, port: string }} Object holding extracted SSH details.
	 */
	const parseSshCommand = (cmd?: string, token?: string) => {
		let user = null;
		let host = "localhost";
		let port = "2222";
		if (!cmd && !token) return { user, host, port };
		const match = cmd?.match(/ssh\s+(?:\s+-p\s+(\d+))?\s+([^@\s]+)@([^\s]+)/);
		if (match) {
			if (match[1]) port = match[1];
			user = match[2];
			host = match[3];
		}
		if (!user) user = token ?? null;
		return { user, host, port };
	};

	const { user, host, port } = parseSshCommand(
		sandboxInfo?.sshCommand,
		sandboxInfo?.token,
	);

	const VSCODE_DEEP_LINK = `vscode://vscode-remote/ssh-remote+${user}@${host}:${port}/sandbox`;
	const CURSOR_DEEP_LINK = `cursor://vscode-remote/ssh-remote+${user}@${host}:${port}/sandbox`;
	const JETBRAINS_DEEP_LINK = `jetbrains-gateway://connect/ssh?host=${host}&port=${port}&user=${user}&projectPath=/sandbox`;

	const displaySshCommand =
		sandboxInfo?.sshCommand || `ssh ${user}@${host} -p ${port}`;

	const handleCopySsh = () => {
		navigator.clipboard.writeText(displaySshCommand);
		setCopied(true);
		setTimeout(() => setCopied(false), 1500);
	};

	const getDeepLink = () => {
		if (activeIde === SupportedIDEs.vscode) return VSCODE_DEEP_LINK;
		if (activeIde === SupportedIDEs.cursor) return CURSOR_DEEP_LINK;
		return JETBRAINS_DEEP_LINK;
	};

	const getIdeLabel = () => {
		if (activeIde === SupportedIDEs.vscode) return "VS Code";
		if (activeIde === SupportedIDEs.cursor) return "Cursor";
		return "JetBrains";
	};

	return (
		<div ref={containerRef} className="relative flex items-center gap-2">
			<div className={!sandboxInfo ? "opacity-55" : ""}>
				<div className="flex h-8 items-center rounded-lg border border-border bg-muted p-0.5 overflow-hidden">
					<button
						type="button"
						onClick={() => setActivePlatform(LanguageType.DOTNET)}
						className={
							"h-full rounded px-2.5 text-[10px] font-bold uppercase tracking-wide transition-all border " +
							(activePlatform === LanguageType.DOTNET
								? "border-primary/30 bg-primary/10 text-primary"
								: "border-transparent text-muted-foreground hover:text-foreground")
						}
					>
						.NET
					</button>
					<button
						type="button"
						onClick={() => setActivePlatform(LanguageType.JAVA)}
						className={
							"h-full rounded px-2.5 text-[10px] font-bold uppercase tracking-wide transition-all border " +
							(activePlatform === LanguageType.JAVA
								? "border-primary/30 bg-primary/10 text-primary"
								: "border-transparent text-muted-foreground hover:text-foreground")
						}
					>
						Java
					</button>

					<a
						href={sandboxInfo ? getDeepLink() : undefined}
						target={sandboxInfo ? "_blank" : undefined}
						rel="noreferrer"
						className={
							"flex h-full items-center gap-1.5 border-r px-3 text-xs font-semibold transition-colors " +
							(sandboxInfo
								? "cursor-pointer text-primary hover:bg-accent hover:text-primary"
								: "pointer-events-none cursor-not-allowed text-muted-foreground")
						}
					>
						{loading ? (
							<RefreshCw className="size-3.5 animate-spin text-muted-foreground" />
						) : (
							<Code2 className="size-3.5" />
						)}
						<span className="hidden @[220px]:inline">
							Remote IDE: {getIdeLabel()}
						</span>
						<span className="@[220px]:hidden">{getIdeLabel()}</span>
						<ExternalLink className="size-3 shrink-0" />
					</a>

					<button
						type="button"
						onClick={() => {
							if (sandboxInfo) setShowDropdown((p) => !p);
						}}
						disabled={!sandboxInfo}
						className={
							"h-full px-2 text-muted-foreground transition-colors " +
							(sandboxInfo
								? "cursor-pointer hover:bg-accent hover:text-foreground"
								: "cursor-not-allowed")
						}
					>
						<ChevronRight
							className={
								"size-3.5 transition-transform " +
								(showDropdown ? "rotate-180" : "")
							}
						/>
					</button>
				</div>
			</div>

			{showDropdown && (
				<div className="absolute right-0 top-10 z-50 w-56 rounded-lg border bg-popover py-1.5 shadow-xl">
					<div className="mb-1 flex items-center justify-between border-b px-3 py-1 pb-1.5">
						<span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
							Select Gateway
						</span>
						<button
							type="button"
							onClick={fetchSandboxSsh}
							className="flex items-center gap-0.5 text-[9px] font-semibold text-primary hover:text-primary/80"
						>
							<RefreshCw className="size-2.5" />
							<span>Refresh</span>
						</button>
					</div>

					{[
						SupportedIDEs.vscode,
						SupportedIDEs.cursor,
						SupportedIDEs.jetbrains,
					].map((ide) => (
						<button
							key={ide}
							type="button"
							onClick={() => {
								setActiveIde(ide);
								setShowDropdown(false);
							}}
							className={
								"flex w-full items-center justify-between px-3 py-1.5 text-left text-xs transition-colors " +
								(activeIde === ide
									? "bg-primary/10 font-semibold text-primary"
									: "text-popover-foreground hover:bg-accent hover:text-accent-foreground")
							}
						>
							<span>
								{ide === SupportedIDEs.vscode
									? "VS Code Remote"
									: ide === SupportedIDEs.cursor
										? "Cursor Remote"
										: "JetBrains Gateway"}
							</span>
							<span className="font-mono text-[9px] text-muted-foreground">
								{ide}://
							</span>
						</button>
					))}

					<hr className="my-1.5 border-border" />

					<div className="px-2 pb-1">
						<span className="mb-1 block px-1 text-[8px] font-bold uppercase tracking-wider text-muted-foreground">
							SSH Command
						</span>
						<button
							type="button"
							onClick={handleCopySsh}
							className="flex w-full items-center justify-between rounded border bg-muted p-1.5 font-mono text-[10px] transition-all hover:bg-muted/80"
						>
							<span className="max-w-[140px] truncate">
								{displaySshCommand}
							</span>
							{copied ? (
								<Check className="size-3 shrink-0 text-emerald-500" />
							) : (
								<Copy className="size-3 shrink-0 text-muted-foreground" />
							)}
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
