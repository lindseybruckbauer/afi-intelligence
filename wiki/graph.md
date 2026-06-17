# Knowledge Graph

Policy relationships across the AFI corpus — publications, directives, and the connections between them.

<div class="usaf-disclaimer">
Nodes represent publications in the corpus and external directives they reference.
Dashed red circles = coverage gaps (restricted or physical-only publications).
Silver nodes = external directives (DoDIs, DAFPDs) not in the corpus.
</div>

<div id="graph-container" style="position:relative;min-height:640px;">
  <p style="padding:2rem;color:var(--md-default-fg-color--light)">Loading knowledge graph...</p>
</div>

## Edge Types

| Edge | Meaning |
|------|---------|
| Gold solid | Publication **implements** a directive |
| Blue dashed | Publication **references** another publication |
| Silver dotted | Publication **supersedes** a prior version |

## Node Types

| Node | Shape | Description |
|------|-------|-------------|
| Solid color | Filled circle | Publication in corpus — click to open wiki page |
| Dashed red outline | Empty circle | Coverage gap — publication exists but is inaccessible |
| Silver, smaller | Small circle | External directive (DoDI, DAFPD) — not in corpus |

## How to Use

- **Zoom:** scroll wheel
- **Pan:** click and drag background
- **Move node:** click and drag a node
- **Highlight connections:** hover over a node
- **Open wiki page:** click a filled node
- **Filter:** use the series and type dropdowns above the graph

## Reading the Graph

The graph reveals policy architecture that's hard to see from individual documents:

- **Clusters** around a directive = multiple AFIs implementing the same higher-level policy
- **Isolated nodes** = publications with few cross-references (potential integration gaps)
- **Coverage gap nodes (red dashed)** = policy domains where content exists but can't be analyzed
- **High-degree nodes** = publications that are heavily cross-referenced across the corpus
