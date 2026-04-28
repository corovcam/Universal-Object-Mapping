#!/bin/bash

# Fix Neo4j ETL export where datetimes are exported as strings
cypher-shell --format plain <<EOF
CALL apoc.periodic.iterate(
  "MATCH (n) RETURN n",
  "
  UNWIND keys(n) AS key
  WITH n, key, n[key] AS val
  
  // Regex updated to optionally allow 'Z' or '+HH:MM' / '-HH:MM' at the end
  WHERE val =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]+(Z|[+-][0-9]{2}:[0-9]{2})?$'
  
  // Switch to datetime() to respect/apply timezones
  CALL apoc.create.setProperty(n, key, datetime(replace(val, ' ', 'T')))
  YIELD node
  RETURN count(*)
  ",
  {batchSize: 10000, parallel: true}
)
EOF

# Fix Neo4j ETL export where dates are exported as strings
cypher-shell --format plain <<EOF
CALL apoc.periodic.iterate(
  "MATCH (n) RETURN n",
  "
  UNWIND keys(n) AS key
  WITH n, key, n[key] AS val
  
  WHERE val =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  
  // Switch to date()
  CALL apoc.create.setProperty(n, key, date(val))
  YIELD node
  RETURN count(*)
  ",
  {batchSize: 10000, parallel: true}
)
EOF

# Create indexes on all properties of all node labels and relationship types to improve query performance

cypher-shell --format plain <<EOF
CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName
UNWIND nodeLabels AS label
WITH label, propertyName
WHERE label IS NOT NULL AND propertyName IS NOT NULL
WITH label, propertyName, 
     'idx_node_' + label + '_' + propertyName AS idxName
CALL apoc.cypher.runSchema(
  'CREATE INDEX `' + idxName + '` IF NOT EXISTS FOR (n:`' + label + '`) ON (n.`' + propertyName + '`)', 
  {}
) YIELD value
RETURN 'Created node index: ' + idxName AS Status;
EOF

cypher-shell --format plain <<EOF
CALL db.schema.relTypeProperties() YIELD relType, propertyName
WHERE relType IS NOT NULL AND propertyName IS NOT NULL
WITH replace(replace(relType, ':`', ''), '`', '') AS cleanRelType, propertyName
WITH cleanRelType, propertyName, 
     'idx_rel_' + cleanRelType + '_' + propertyName AS idxName
CALL apoc.cypher.runSchema(
  'CREATE INDEX `' + idxName + '` IF NOT EXISTS FOR ()-[r:`' + cleanRelType + '`]-() ON (r.`' + propertyName + '`)', 
  {}
) YIELD value
RETURN 'Created relationship index: ' + idxName AS Status;
EOF
