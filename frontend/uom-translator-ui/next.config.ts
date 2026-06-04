import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	// cacheComponents: true,
	output: "standalone",
	logging: {
		browserToTerminal: true,
		fetches: {
			fullUrl: true,
		},
	},
};

export default nextConfig;
