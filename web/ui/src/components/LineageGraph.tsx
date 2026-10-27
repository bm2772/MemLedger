// explain(claim_id) as a graph (slide 6): sources (rounded) and memories (boxes), one edge per derivation.
// Solid edge = verifier-confirmed support (supported_by); dashed = only in the context window (exposed_to).
import { useMemo } from "react";
import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import type { Explain, ExplainNode } from "../api";

type Data = { title: string; kind: string; bad: boolean; root: boolean; trust?: number; status?: string };

function LNode({ data }: NodeProps<Node<Data>>) {
  const src = data.kind !== "memory";
  return (
    <div className={`lnode ${src ? "src" : ""} ${data.bad ? "bad" : ""} ${data.root ? "root" : ""}`}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="spread"><span className="k">{data.kind}</span>
        {data.status && <span className="k" style={{ color: data.bad ? "var(--danger)" : "var(--accent)" }}>{data.status}{data.trust !== undefined ? ` · ${data.trust.toFixed(2)}` : ""}</span>}
      </div>
      <div style={{ marginTop: 3, lineHeight: 1.35 }}>{data.title}</div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
const nodeTypes = { l: LNode };

export function LineageGraph({ explain, sourceText, onOpen }: { explain: Explain; sourceText: (id: string) => string | undefined; onOpen?: (claimId: string) => void }) {
  const { nodes, edges } = useMemo(() => {
    const nodes = new Map<string, Node<Data>>();
    const edges: Edge[] = [];
    const clip = (t: string) => (t.length > 90 ? t.slice(0, 87) + "…" : t);
    const walk = (e: Explain, root: boolean) => {
      nodes.set(e.claim, { id: e.claim, type: "l", position: { x: 0, y: 0 }, data: { title: clip(e.text), kind: "memory", bad: e.status === "quarantined", root, trust: e.trust, status: e.status } });
      for (const d of e.lineage) {
        for (const n of d.exposed_to) {
          const id = visit(n);
          const supported = id in d.supported_by;
          edges.push({
            id: `${d.derivation}-${id}`, source: id, target: e.claim, animated: false,
            style: { strokeDasharray: supported ? undefined : "5 4", stroke: "var(--faint)", strokeWidth: 1.5 },
          });
        }
      }
    };
    const visit = (n: ExplainNode): string => {
      if ("lineage" in n) { if (!nodes.has(n.claim)) walk(n, false); return n.claim; }
      if (n.type === "source") {
        if (!nodes.has(n.id)) nodes.set(n.id, { id: n.id, type: "l", position: { x: 0, y: 0 }, data: { title: clip(sourceText(n.id) ?? n.id), kind: n.kind, bad: n.flagged, root: false, status: n.flagged ? "flagged" : undefined } });
        return n.id;
      }
      if (!nodes.has(n.id)) nodes.set(n.id, { id: n.id, type: "l", position: { x: 0, y: 0 }, data: { title: n.id, kind: "memory", bad: false, root: false } });
      return n.id;
    };
    walk(explain, true);

    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: "TB", nodesep: 28, ranksep: 64 });
    g.setDefaultEdgeLabel(() => ({}));
    for (const n of nodes.values()) g.setNode(n.id, { width: 220, height: 72 });
    for (const e of edges) g.setEdge(e.source, e.target);
    dagre.layout(g);
    for (const n of nodes.values()) {
      const p = g.node(n.id);
      n.position = { x: p.x - 110, y: p.y - 36 };
    }
    return { nodes: [...nodes.values()], edges };
  }, [explain, sourceText]);

  return (
    <div className="lineage">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}
        onNodeClick={(_, n) => n.data.kind === "memory" && !n.data.root && onOpen?.(n.id)} colorMode="system">
        <Background gap={20} size={1} color="var(--line)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
