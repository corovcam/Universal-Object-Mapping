import type { Toolkit } from "@assistant-ui/react";
import { z } from "zod";

/**
 * Registry of client-side tools available to the assistant-ui chat runtime.
 * Enables the LLM model to call specific local functions that can render custom UI cards
 * or access client capabilities.
 */
export const uomToolkit: Toolkit = {
	/**
	 * Client-side tool that queries and displays weather information.
	 * Currently acts as a showcase of human-in-the-loop interaction patterns.
	 */
	getWeather: {
		type: "human",
		description: "Get current weather for a location",
		parameters: z.object({
			location: z.string().describe("City name or zip code"),
			unit: z.enum(["celsius", "fahrenheit"]).default("celsius"),
		}),
		render: ({ args, result }) => {
			if (!result) return <div>Fetching weather for {args.location}...</div>;
			return (
				<div className="weather-card">
					<h3>{args.location}</h3>
					<p>
						{result.temperature}° {args.unit}
					</p>
					<p>{result.conditions}</p>
				</div>
			);
		},
	},
	/**
	 * Backend client-side tool helper. Acts as a template tool for
	 * rendering custom schema structure details in the chat thread directly.
	 */
	databaseTool: {
		type: "backend",
		// description: "Get current weather for a location",
		// parameters: z.object({
		//   location: z.string().describe("City name or zip code"),
		//   unit: z.enum(["celsius", "fahrenheit"]).default("celsius"),
		// }),
		render: ({ args, result }) => {
			if (!result) return <div>Fetching weather for {args.location}...</div>;
			return (
				<div className="weather-card">
					<h3>{args.location}</h3>
					<p>
						{result.temperature}° {args.unit}
					</p>
					<p>{result.conditions}</p>
				</div>
			);
		},
	},
	// Add more tools here
};
