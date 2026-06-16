import fs from 'fs';
import path from 'path';

// --- CONFIGURATION ---
const TYPE_DOC_NAV_PATH = path.join(process.cwd(), 'navigation.json');
const MINTLIFY_DOCS_PATH = path.join(process.cwd(), '../../external/uom-docs/docs.json');
const TARGET_TAB_NAME = 'Frontend Code Reference';

// Prefix prepended to all paths (e.g., if files are under 'docs/frontend/...')
// If TypeDoc outputs directly to the docs root, leave this as an empty string.
const ROUTE_PREFIX = 'frontend_code_reference'; 

// --- HELPER FUNCTIONS ---

// Cleans extensions and prepends the route prefix if specified
function cleanPath(filePath) {
  const withoutExt = filePath.replace(/\.mdx?$/, '');
  return ROUTE_PREFIX ? `${ROUTE_PREFIX}/${withoutExt}` : withoutExt;
}

// Recursively transforms TypeDoc AST nodes into Mintlify navigation structures
function transformNode(node) {
  // Case 1: Node has nested children (becomes a nested group)
  if (node.children && node.children.length > 0) {
    const groupBlock = {
      group: node.title,
      pages: node.children.map(child => transformNode(child))
    };

    // If the folder container itself has an index/overview page
    if (node.path) {
      groupBlock.root = cleanPath(node.path);
    }

    return groupBlock;
  }

  // Case 2: Leaf node with a direct path (becomes a simple string route)
  if (node.path) {
    return cleanPath(node.path);
  }

  // Fallback fallback case for empty groups
  return node.title;
}

// --- MAIN PIPELINE ---
function syncNavigation() {
  // 1. Load source files
  if (!fs.existsSync(TYPE_DOC_NAV_PATH) || !fs.existsSync(MINTLIFY_DOCS_PATH)) {
    console.error('❌ Error: Ensure both navigation.json and docs.json exist.');
    process.exit(1);
  }

  const typeDocNav = JSON.parse(fs.readFileSync(TYPE_DOC_NAV_PATH, 'utf8'));
  const mintDocs = JSON.parse(fs.readFileSync(MINTLIFY_DOCS_PATH, 'utf8'));

  // 2. Map TypeDoc structure to Mintlify Groups
  console.log('Parsing TypeDoc navigation tree...');
  const generatedGroups = typeDocNav.map(rootNode => transformNode(rootNode));

  // 3. Locate or create the target tab inside docs.json
  if (!mintDocs.navigation) {
    mintDocs.navigation = { tabs: [] };
  } else if (!mintDocs.navigation.tabs) {
    mintDocs.navigation.tabs = [];
  }

  const existingTab = mintDocs.navigation.tabs.find(t => t.tab === TARGET_TAB_NAME);

  if (existingTab) {
    console.log(`Updating existing tab: "${TARGET_TAB_NAME}"`);
    existingTab.groups = generatedGroups;
    existingTab.directory = 'accordion'; // Ensures smooth collapsible tree views
  } else {
    console.log(`Creating fresh tab: "${TARGET_TAB_NAME}"`);
    mintDocs.navigation.tabs.push({
      tab: TARGET_TAB_NAME,
      directory: 'accordion',
      groups: generatedGroups
    });
  }

  // 4. Write updates back to docs.json
  fs.writeFileSync(MINTLIFY_DOCS_PATH, JSON.stringify(mintDocs, null, 2), 'utf8');
  console.log('✅ Successfully updated docs.json with modern frontend references!');
  fs.unlinkSync(TYPE_DOC_NAV_PATH); // Clean up the intermediate navigation file
}

syncNavigation();