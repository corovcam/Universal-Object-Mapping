import { SourceUnit } from "./convert";
import { ORMType } from "./orm-type";

export interface AdvisorRunQuery {
  id: string;
  query: SourceUnit;
  weight: number;
}

export interface AdvisorRunRequest {
  sourceOrm: ORMType;
  entities: SourceUnit[];
  queries: AdvisorRunQuery[];
  maxMemoryBytes: number;
  maxFrameworksToSelect: number;
  targetFrameworks?: ORMType[];
  /** When true, uses execution plan analysis to predict costs instead of running queries */
  usePrediction?: boolean;
}

export interface BenchmarkMeasurementDto {
  meanDurationMilliseconds: number;
  allocatedBytes: number;
  /** Predicted cost from execution plan analysis (if available) */
  predictedCost?: number;
  /** Predicted row count from execution plan (if available) */
  predictedRows?: number;
}

export type MeasurementsByFramework = Record<ORMType, BenchmarkMeasurementDto>;
export type AdvisorMeasurements = Record<string, MeasurementsByFramework>;

/** Result of query execution plan prediction for a single framework */
export interface QueryPlanPredictionDto {
  framework: ORMType;
  sqlQuery: string;
  estimatedCost: number;
  estimatedRows: number;
  estimatedCpuCost: number;
  estimatedIoCost: number;
  isSuccess: boolean;
  errorMessage?: string;
}

export type PredictionsByFramework = Record<ORMType, QueryPlanPredictionDto>;
export type AdvisorPredictions = Record<string, PredictionsByFramework>;

export interface AdvisorRunResult {
  selectedFrameworks: ORMType[];
  queryAssignments: Record<string, ORMType>;
  measurements: AdvisorMeasurements;
  /** Optional predictions from execution plan analysis (only populated when usePrediction is true) */
  predictions?: AdvisorPredictions;
  /** Indicates whether the result was based on predicted costs (true) or actual execution (false) */
  usedPrediction?: boolean;
}

/** Response containing predicted costs for all frameworks */
export interface QueryPlanPredictionResult {
  predictions: QueryPlanPredictionDto[];
  recommendedFramework?: ORMType;
  predictionsByQuery: AdvisorPredictions;
}
