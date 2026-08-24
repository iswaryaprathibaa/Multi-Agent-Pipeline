import type { NodeName, NodeStatus } from "@/lib/types";

const COLORS: Record<NodeStatus, [string, string, string]> = {
  pending: ["#f1f5f9", "#94a3b8", "#64748b"],
  active: ["#dbeafe", "#2563eb", "#1e3a8a"],
  done: ["#dcfce7", "#16a34a", "#14532d"],
  flagged: ["#fef3c7", "#d97706", "#78350f"],
};

const NODE_ORDER: NodeName[] = ["researcher", "writer", "editor", "validator"];
const NEXT_NODE: Record<string, NodeName> = { researcher: "writer", writer: "editor", editor: "validator" };

const NODE_META: Record<NodeName, { emoji: string; title: string; subtitle: string; x: number }> = {
  researcher: { emoji: "\u{1F50E}", title: "Researcher", subtitle: "RAG retrieval + notes", x: 96 },
  writer: { emoji: "✍️", title: "Writer", subtitle: "drafts / revises report", x: 316 },
  editor: { emoji: "\u{1FA84}", title: "Editor", subtitle: "polishes clarity & tone", x: 536 },
  validator: { emoji: "✅", title: "Validator", subtitle: "fact-checks & gates", x: 756 },
};

const RECT_W = 170;
const RECT_H = 90;
const RECT_Y = 95;
const CENTER_Y = 140;
const LOOP_PATH = "M841,95 C841,15 401,15 401,95";

const STRAIGHT_EDGES: Array<{ path: string; target: NodeName | "end" }> = [
  { path: "M64,140 L92,140", target: "researcher" },
  { path: "M266,140 L312,140", target: "writer" },
  { path: "M486,140 L532,140", target: "editor" },
  { path: "M706,140 L752,140", target: "validator" },
  { path: "M926,140 L968,140", target: "end" },
];

export interface PipelineDiagramProps {
  statuses: Record<NodeName, NodeStatus>;
  revisionCount: number;
  looping: boolean;
  finished: boolean;
}

export default function PipelineDiagram({ statuses, revisionCount, looping, finished }: PipelineDiagramProps) {
  const statusOf = (name: NodeName | "start" | "end"): NodeStatus => {
    if (name === "start") return statuses.researcher === "pending" ? "pending" : "done";
    if (name === "end") return finished ? "done" : "pending";
    if (name === "writer" && looping) return "done";
    return statuses[name] ?? "pending";
  };

  const edgeClassMarker = (target: NodeName | "end"): [string, string] => {
    const s = statusOf(target);
    if (s === "active") return ["flow-active", "url(#arrow-blue)"];
    if (s === "done" || s === "flagged") return ["flow-done", "url(#arrow-green)"];
    return ["flow-pending", "url(#arrow-gray)"];
  };

  const loopClass = looping ? "loop-active" : "loop-idle";
  const loopMarker = looping ? "url(#arrow-orange)" : "url(#arrow-gray)";
  const loopLabel = `feedback loop${revisionCount ? ` — revision #${revisionCount}` : ""}`;

  return (
    <div className="diagram-wrap">
      <svg viewBox="0 0 1040 190" width="100%" style={{ minWidth: 760 }} xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="arrow-gray" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#cbd5e1" />
          </marker>
          <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#2563eb" />
          </marker>
          <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#16a34a" />
          </marker>
          <marker id="arrow-orange" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#d97706" />
          </marker>
        </defs>

        {STRAIGHT_EDGES.map(({ path, target }) => {
          const [cls, marker] = edgeClassMarker(target);
          return <path key={target} d={path} className={cls} markerEnd={marker} />;
        })}
        <path d={LOOP_PATH} className={loopClass} markerEnd={loopMarker} />

        {STRAIGHT_EDGES.filter(({ target }) => edgeClassMarker(target)[0] === "flow-active").map(({ path, target }) => (
          <circle key={`dot-${target}`} r={5} fill="#2563eb">
            <animateMotion dur="0.9s" repeatCount="indefinite" path={path} />
          </circle>
        ))}
        {looping && (
          <circle r={5} fill="#d97706">
            <animateMotion dur="1.4s" repeatCount="indefinite" path={LOOP_PATH} />
          </circle>
        )}

        {NODE_ORDER.map((name) => {
          const status = statuses[name] ?? "pending";
          const [fill, stroke, text] = COLORS[status];
          const pulse = status === "active" ? "pulse-blue" : status === "flagged" ? "pulse-orange" : "";
          const meta = NODE_META[name];
          const cx = meta.x + RECT_W / 2;
          return (
            <g key={name} className={pulse}>
              <rect x={meta.x} y={RECT_Y} width={RECT_W} height={RECT_H} rx={16} fill={fill} stroke={stroke} strokeWidth={2.5} />
              <text x={cx} y={133} textAnchor="middle" fontSize={16} fontWeight={700} fill={text}>
                {meta.emoji} {meta.title}
              </text>
              <text x={cx} y={153} textAnchor="middle" fontSize={11} fill={text} opacity={0.85}>
                {meta.subtitle}
              </text>
            </g>
          );
        })}

        {(["start", "end"] as const).map((name) => {
          const status = statusOf(name);
          const [fill, stroke, text] = COLORS[status];
          const cx = name === "start" ? 40 : 996;
          return (
            <g key={name}>
              <circle cx={cx} cy={CENTER_Y} r={24} fill={fill} stroke={stroke} strokeWidth={3} />
              <text x={cx} y={145} textAnchor="middle" fontSize={11} fontWeight={700} fill={text}>
                {name.toUpperCase()}
              </text>
            </g>
          );
        })}

        <text x={621} y={30} textAnchor="middle" fontSize={12} fontWeight={looping ? 700 : 500} fill={looping ? "#d97706" : "#94a3b8"}>
          {loopLabel}
        </text>
      </svg>

      <div className="legend">
        <span>
          <i style={{ background: "#94a3b8" }} />
          pending
        </span>
        <span>
          <i style={{ background: "#2563eb" }} />
          active
        </span>
        <span>
          <i style={{ background: "#16a34a" }} />
          done
        </span>
        <span>
          <i style={{ background: "#d97706" }} />
          needs revision
        </span>
      </div>
    </div>
  );
}

export { NODE_ORDER, NEXT_NODE };
