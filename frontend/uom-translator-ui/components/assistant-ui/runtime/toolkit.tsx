"use client";

import { type Toolkit } from "@assistant-ui/react";
import { z } from "zod";

export const uomToolkit: Toolkit = {
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
          <p>{result.temperature}° {args.unit}</p>
          <p>{result.conditions}</p>
        </div>
      );
    },
  },
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
          <p>{result.temperature}° {args.unit}</p>
          <p>{result.conditions}</p>
        </div>
      );
    },
  },
  // Add more tools here
};
