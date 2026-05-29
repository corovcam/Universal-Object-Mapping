"use client";

import { AssistantRuntime, AssistantRuntimeProvider, Suggestions, useAui } from "@assistant-ui/react";
// import { uomToolkit } from "./toolkit";

const efcoreToMongoInput = await fetch('/input-efcore-mongodb.txt').then(r => r.text()).catch((e) => console.error(e));
const efcoreToNeo4jInput = await fetch('/input-efcore-neo4j.txt').then(r => r.text()).catch((e) => console.error(e));
const dapperToMongoInput = await fetch('/input-dapper-mongodb.txt').then(r => r.text()).catch((e) => console.error(e))
const nhibernateToMongoInput = await fetch('/input-nhibernate-mongodb.txt').then(r => r.text()).catch((e) => console.error(e));

export function UomRuntime({ runtime, children }: { runtime: AssistantRuntime, children: React.ReactNode }) {
  const suggestions = []
  
  if (efcoreToMongoInput) {
    suggestions.push({
      title: "EF Core to Spring Data MongoDB",
      label: "Sample translation from EF Core 10 to Spring Data MongoDB 5.0",
      prompt: efcoreToMongoInput,
    });
  }
  if (efcoreToNeo4jInput) {
    suggestions.push({
      title: "EF Core to Spring Data Neo4j",
      label: "Sample translation from EF Core 10 to Spring Data Neo4j 8.0",
      prompt: efcoreToNeo4jInput,
    });
  }
  if (dapperToMongoInput) {
    suggestions.push({
      title: "Dapper to Spring Data MongoDB",
      label: "Sample translation from Dapper to Spring Data MongoDB",
      prompt: dapperToMongoInput,
    });
  }
  if (nhibernateToMongoInput) {
    suggestions.push({
      title: "NHibernate to Spring Data MongoDB",
      label: "Sample translation from NHibernate to Spring Data MongoDB",
      prompt: nhibernateToMongoInput,
    });
  }
  
  const aui = useAui({
    // tools: Tools({ toolkit: uomToolkit }),
    suggestions: Suggestions(suggestions),
  });

  return (
    <AssistantRuntimeProvider aui={aui} runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
