FROM langchain/langgraph-api:3.13-wolfi

RUN apk update && apk add nodejs-24 npm && node --version && npm --version

# -- Adding local package . --
ADD . /deps/orchestrator
# -- End of local package . --

# -- Installing all local dependencies --
RUN for dep in /deps/*; do             echo "Installing $dep";             if [ -d "$dep" ]; then                 echo "Installing $dep";                 (cd "$dep" && PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir -c /api/constraints.txt -e .);             fi;         done
# -- End of local dependencies install --
ENV LANGSERVE_GRAPHS='{"universal-object-mapping-translator": {"path": "/deps/orchestrator/src/react_agent/graph.py:graph", "description": "Migrates code database entity schemas, mappings/context/settings and queries between Object-Relational Mapping (ORM), Object-Graph Mapping (OGM), and Object-Document Mapping (ODM) frameworks by performing LLM-based translation and validation workflow. Currently supports translation from .NET (Entity Framework Core, NHibernate, Dapper) to Java frameworks (Spring Data MongoDB, Spring Data Neo4j).\nTranslation Workflow:\n1. User provides source .NET schema, mappings/context/settings and queries.\n2. Orchestrator extracts target frameworks and checks user intent.\n3. Orchestrator connects to database via MCP to inspect DB schema mapping context.\n4. Generates code and testing harnesses without tools.\n5. Systematically validates schema, compiles queries, checks data equivalence, and evaluates if the result is correct (`ACCEPT` or `REJECT`).\n6. If rejected, it loops back to correct the code (up to 3 times) before eventually falling back to a human-in-the-loop if unresolved."}}'



# -- Ensure user deps didn't inadvertently overwrite langgraph-api
RUN mkdir -p /api/langgraph_api /api/langgraph_runtime /api/langgraph_license && touch /api/langgraph_api/__init__.py /api/langgraph_runtime/__init__.py /api/langgraph_license/__init__.py
RUN PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir --no-deps -e /api
# -- End of ensuring user deps didn't inadvertently overwrite langgraph-api --
# -- Removing build deps from the final image ~<:===~~~ --
RUN pip uninstall -y pip setuptools wheel
RUN rm -rf /usr/local/lib/python*/site-packages/pip* /usr/local/lib/python*/site-packages/setuptools* /usr/local/lib/python*/site-packages/wheel* && find /usr/local/bin -name "pip*" -delete || true
RUN rm -rf /usr/lib/python*/site-packages/pip* /usr/lib/python*/site-packages/setuptools* /usr/lib/python*/site-packages/wheel* && find /usr/bin -name "pip*" -delete || true
RUN uv pip uninstall --system pip setuptools wheel && rm /usr/bin/uv /usr/bin/uvx

WORKDIR /deps/orchestrator