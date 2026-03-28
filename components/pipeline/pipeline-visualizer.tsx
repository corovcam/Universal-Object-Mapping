"use client";

import { StepIndicator } from "./step-indicator";
import type { PipelineStep } from "@/lib/types";

interface PipelineVisualizerProps {
  currentStep: PipelineStep;
  completedSteps: PipelineStep[];
}

const PIPELINE_STEPS: { id: PipelineStep; label: string; description: string }[] = [
  {
    id: "extract_input",
    label: "Extract Input",
    description: "Parsing source code and detecting framework",
  },
  {
    id: "schema_inspection",
    label: "Schema Inspection",
    description: "Analyzing database schema and relationships",
  },
  {
    id: "council_of_models",
    label: "Council of Models",
    description: "Consulting multiple AI models for best approach",
  },
  {
    id: "translation_agent",
    label: "Translation Agent",
    description: "Generating translated code",
  },
];

export function PipelineVisualizer({
  currentStep,
  completedSteps,
}: PipelineVisualizerProps) {
  const getStepStatus = (stepId: PipelineStep): "pending" | "active" | "completed" => {
    if (completedSteps.includes(stepId)) return "completed";
    if (stepId === currentStep) return "active";
    return "pending";
  };

  if (currentStep === "idle" || currentStep === "error") {
    return null;
  }

  return (
    <div className="px-4 py-3 border-b bg-muted/30">
      <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2 scrollbar-hide">
        {PIPELINE_STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1 min-w-0">
            <StepIndicator
              label={step.label}
              description={step.description}
              status={getStepStatus(step.id)}
              stepNumber={index + 1}
            />
            {index < PIPELINE_STEPS.length - 1 && (
              <div className="flex-shrink-0 w-8 mx-1 hidden sm:block">
                <div
                  className={`h-0.5 w-full transition-colors duration-300 ${
                    completedSteps.includes(step.id)
                      ? "bg-primary"
                      : "bg-border"
                  }`}
                />
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Mobile: Show current step details */}
      <div className="sm:hidden mt-2">
        <p className="text-xs text-muted-foreground">
          {PIPELINE_STEPS.find((s) => s.id === currentStep)?.description}
        </p>
      </div>
    </div>
  );
}
