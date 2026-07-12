import React, { useEffect, useRef, useState, useCallback } from "react";
import { Network, ZoomIn, ZoomOut, Maximize2, Download, RefreshCw, FileText, Upload, Search, X, BarChart2, Info } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import Navbar from "../components/Navbar";
import { generateMindMap, generateMindMapFromFile } from "../api";

cytoscape.use(dagre);

const SAMPLE = `A Database Management System (DBMS) is software used to manage databases.
A Database stores structured data. Key components are Tables which have Columns and Rows.
SQL (Structured Query Language) is used to query databases.
Common SQL commands: SELECT, INSERT, UPDATE, DELETE.
A Primary Key uniquely identifies each row. A Foreign Key links two Tables.
Indexes speed up data retrieval. Transactions ensure data integrity using ACID properties.`;

const TYPE_CONFIG = {
  central:    { bg: "#061e2a", border: "#00e5ff", label: "#00e5ff", shadow: "#00e5ff", w: 160, h: 58, fontSize: 15, fontWeight: "bold" },
  subconcept: { bg: "#061a14", border: "#00c896", label: "#00c896", shadow: "#00c896", w: 135, h: 50, fontSize: 13, fontWeight: "600" },
  detail:     { bg: "#130a2a", border: "#a855f7", label: "#c084fc", shadow: "#a855f7", w: 115, h: 44, fontSize: 12, fontWeight: "normal" },
  example:    { bg: "#1c1203", border: "#f59e0b", label: "#fbbf24", shadow: "#f59e0b", w: 115, h: 44, fontSize: 12, fontWeight: "normal" },
};

const LEGEND = [
  { type: "central",    label: "Main Topic",   color: "#00e5ff" },
  { type: "subconcept", label: "Subtopic",      color: "#00c896" },
  { type: "detail",     label: "Detail",        color: "#a855f7" },
  { type: "example",    label: "Example",       color: "#f59e0b" },
];

const buildCyStyles = () => {
  const base = [
    {
      selector: "node",
      style: {
        "background-color": "#061e2a",
        "border-color": "#00e5ff",
        "border-width": 2,
        label: "data(label)",
        color: "#ffffff",
        "font-size": "13px",
        "font-family": "Space Grotesk, sans-serif",
        "text-valign": "center",
        "text-halign": "center",
        "shape": "round-rectangle",
        "text-wrap": "wrap",
        "text-max-width": "130px",
        "transition-property": "border-color, background-color, opacity, border-width",
        "transition-duration": "0.25s",
      },
    },
    {
      selector: "node:selected",
      style: { "border-width": 4, "border-color": "#ffffff", "background-color": "#0a2535" },
    },
    {
      selector: "node.dimmed",
      style: { opacity: 0.2 },
    },
    {
      selector: "node.highlighted",
      style: { "border-width": 4, "border-color": "#ffffff", opacity: 1 },
    },
    {
      selector: "edge",
      style: {
        width: 2,
        "line-color": "#1e4a5a",
        "target-arrow-color": "#1e4a5a",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": "10px",
        "font-family": "Space Grotesk, sans-serif",
        color: "#6b7fa3",
        "text-background-opacity": 0.85,
        "text-background-color": "#080e1a",
        "text-background-shape": "round-rectangle",
        "text-background-padding": "3px",
        "text-rotation": "autorotate",
        opacity: 0.75,
        "transition-property": "opacity",
        "transition-duration": "0.25s",
      },
    },
    {
      selector: "edge:selected, edge.highlighted",
      style: { "line-color": "#00e5ff", "target-arrow-color": "#00e5ff", width: 3, opacity: 1 },
    },
    {
      selector: "edge.dimmed",
      style: { opacity: 0.08 },
    },
  ];

  // Per-type styles
  Object.entries(TYPE_CONFIG).forEach(([type, cfg]) => {
    base.push({
      selector: `node[type="${type}"]`,
      style: {
        "background-color": cfg.bg,
        "border-color": cfg.border,
        color: cfg.label,
        "font-size": `${cfg.fontSize}px`,
        "font-weight": cfg.fontWeight,
        width: `${cfg.w}px`,
        height: `${cfg.h}px`,
        "shadow-blur": type === "central" ? 20 : 12,
        "shadow-color": cfg.shadow,
        "shadow-offset-x": 0,
        "shadow-offset-y": 0,
        "shadow-opacity": type === "central" ? 0.9 : 0.6,
      },
    });
  });

  return base;
};

const getLayoutConfig = (layoutName) => {
  if (layoutName === "dagre" || layoutName === "dagre-lr") {
    return {
      name: "dagre",
      rankDir: layoutName === "dagre-lr" ? "LR" : "TB",
      nodeSep: 60,
      rankSep: 85,
      animate: true,
      animationDuration: 500,
      fit: true,
      padding: 45,
      nodeDimensionsIncludeLabels: true,
    };
  }
  if (layoutName === "cose") {
    return {
      name: "cose",
      animate: true,
      animationDuration: 500,
      fit: true,
      padding: 45,
      nodeRepulsion: () => 100000,
      idealEdgeLength: () => 130,
      edgeElasticity: () => 100,
      nodeOverlap: 60,
      nodeDimensionsIncludeLabels: true,
    };
  }
  return {
    name: layoutName,
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 45,
    nodeDimensionsIncludeLabels: true,
  };
};

export default function MindMap() {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const fileInputRef = useRef(null);

  const [tab, setTab] = useState("text");
  const [notes, setNotes] = useState(SAMPLE);
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [layout, setLayout] = useState("dagre");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [elements, setElements] = useState(null);
  const [selected, setSelected] = useState(null);
  const [stats, setStats] = useState(null);

  // ── Search / highlight ────────────────────────────────────────────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (!search.trim()) {
      cy.elements().removeClass("dimmed highlighted");
      return;
    }
    const term = search.toLowerCase();
    const matched = cy.nodes().filter(n => n.data("label").toLowerCase().includes(term));
    if (matched.length === 0) {
      cy.elements().removeClass("dimmed highlighted");
      return;
    }
    cy.elements().addClass("dimmed").removeClass("highlighted");
    const neighborhood = matched.union(matched.connectedEdges()).union(matched.connectedEdges().connectedNodes());
    neighborhood.removeClass("dimmed").addClass("highlighted");
  }, [search]);

  // ── Re-run layout on change ───────────────────────────────────────────────
  useEffect(() => {
    if (!cyRef.current || !elements) return;
    const cfg = getLayoutConfig(layout);
    cyRef.current.layout(cfg).run();
  }, [layout]);

  // ── Cytoscape init ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || !elements) return;
    if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null; }

    const nodes = (elements.nodes || []).map(n => ({
      group: "nodes",
      data: {
        id: n.data.id,
        label: n.data.label || n.data.id,
        type: n.data.type || "detail",
        description: n.data.description || "",
      },
    }));
    const edges = (elements.edges || []).map(e => ({
      group: "edges",
      data: {
        id: e.data.id || `${e.data.source}_${e.data.target}`,
        source: e.data.source,
        target: e.data.target,
        label: e.data.label || "",
      },
    }));

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
      style: buildCyStyles(),
      layout: getLayoutConfig(layout),
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
      minZoom: 0.2,
      maxZoom: 4,
    });

    // Click node
    cy.on("tap", "node", evt => {
      const n = evt.target;
      const incoming = n.incomers("edge").map(e => ({
        from: cy.getElementById(e.data("source")).data("label"),
        label: e.data("label"),
      }));
      const outgoing = n.outgoers("edge").map(e => ({
        to: cy.getElementById(e.data("target")).data("label"),
        label: e.data("label"),
      }));
      setSelected({
        id: n.id(), label: n.data("label"), type: n.data("type"),
        description: n.data("description"), degree: n.degree(),
        incoming, outgoing,
      });
    });

    cy.on("tap", evt => { if (evt.target === cy) setSelected(null); });

    cyRef.current = cy;

    // Stats
    const degrees = cy.nodes().map(n => ({ label: n.data("label"), deg: n.degree() }));
    const topNode = degrees.sort((a, b) => b.deg - a.deg)[0];
    setStats({
      nodes: cy.nodes().length,
      edges: cy.edges().length,
      topNode: topNode?.label || "—",
      types: {
        central:    cy.nodes('[type="central"]').length,
        subconcept: cy.nodes('[type="subconcept"]').length,
        detail:     cy.nodes('[type="detail"]').length,
        example:    cy.nodes('[type="example"]').length,
      },
    });

    return () => { if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null; } };
  }, [elements]);

  // ── Generate ─────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setError(""); setSelected(null); setLoading(true);
    try {
      let data;
      if (tab === "file" && uploadedFile) {
        data = await generateMindMapFromFile(uploadedFile);
      } else {
        if (!notes.trim()) { setError("Please enter some study notes."); setLoading(false); return; }
        data = await generateMindMap(notes);
      }
      if (data?.elements) setElements(data.elements);
      else throw new Error("Invalid response from server.");
    } catch (e) {
      setError(e?.response?.data?.detail || "Generation failed. Make sure the backend is running.");
    } finally { setLoading(false); }
  };

  // ── File handlers ─────────────────────────────────────────────────────────
  const handleFileDrop = useCallback(e => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setUploadedFile(f);
  }, []);

  const handleFileSelect = e => { if (e.target.files[0]) setUploadedFile(e.target.files[0]); };

  // ── Controls ──────────────────────────────────────────────────────────────
  const zoomIn  = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.25);
  const fitView = () => { cyRef.current?.fit(); cyRef.current?.center(); };
  const exportPng = () => {
    if (!cyRef.current) return;
    const blob = cyRef.current.png({ output: "blob", bg: "#080e1a", full: true });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `mindmap-${Date.now()}.png`;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  };

  const typeBadge = type => {
    const colors = { central: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40", subconcept: "bg-teal-500/20 text-teal-300 border-teal-500/40", detail: "bg-purple-500/20 text-purple-300 border-purple-500/40", example: "bg-amber-500/20 text-amber-300 border-amber-500/40" };
    return colors[type] || colors.detail;
  };

  return (
    <div className="min-h-screen bg-dark text-white font-grotesk overflow-x-hidden">
      <Navbar />

      <div className="pt-24 px-4 md:px-10 pb-16 max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <section className="bg-card-bg border border-card-border rounded-[30px] p-7">
          <div className="flex items-center gap-3 mb-1">
            <Network className="text-primary-cyan w-6 h-6" />
            <p className="text-xs uppercase tracking-[0.3em] text-primary-cyan">Visual Learning</p>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold">Interactive Concept Mind-Map</h1>
          <p className="text-text-gray mt-1 text-sm max-w-2xl">
            Paste notes or upload a PDF/TXT file. The AI extracts concepts and relationships and renders an interactive visual graph.
          </p>
        </section>

        {error && (
          <div className="flex items-center gap-3 bg-rose-500/10 border border-rose-500/30 text-rose-200 px-5 py-3.5 rounded-[18px] text-sm">
            <X className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* ── Left Panel ── */}
          <div className="lg:col-span-4 space-y-5">

            {/* Input card */}
            <div className="bg-card-bg border border-card-border rounded-[28px] p-5 space-y-4">
              {/* Tabs */}
              <div className="flex bg-black/30 rounded-[14px] p-1 gap-1">
                {[["text", "Text Notes", FileText], ["file", "Upload File", Upload]].map(([id, label, Icon]) => (
                  <button key={id} onClick={() => setTab(id)}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-[10px] text-sm font-medium transition-all ${tab === id ? "bg-primary-cyan/15 text-primary-cyan border border-primary-cyan/30" : "text-text-gray hover:text-white"}`}>
                    <Icon className="w-4 h-4" />{label}
                  </button>
                ))}
              </div>

              {/* Text tab */}
              {tab === "text" && (
                <textarea value={notes} onChange={e => setNotes(e.target.value)}
                  placeholder="Paste your study notes here..."
                  className="w-full h-56 bg-black/40 border border-white/10 rounded-[16px] p-4 text-sm text-white focus:outline-none focus:border-primary-cyan resize-none transition-colors" />
              )}

              {/* File tab */}
              {tab === "file" && (
                <div
                  onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`cursor-pointer h-56 rounded-[16px] border-2 border-dashed flex flex-col items-center justify-center gap-3 transition-all ${dragOver ? "border-primary-cyan bg-primary-cyan/10" : "border-white/15 hover:border-primary-cyan/50 hover:bg-white/5"}`}>
                  <input ref={fileInputRef} type="file" accept=".pdf,.txt" className="hidden" onChange={handleFileSelect} />
                  <Upload className={`w-10 h-10 ${dragOver ? "text-primary-cyan" : "text-white/30"}`} />
                  {uploadedFile ? (
                    <div className="text-center">
                      <p className="text-sm font-semibold text-primary-cyan">{uploadedFile.name}</p>
                      <p className="text-xs text-text-gray mt-1">{(uploadedFile.size / 1024).toFixed(1)} KB — Click to change</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-sm font-medium text-white/60">Drag & drop PDF or TXT</p>
                      <p className="text-xs text-text-gray mt-1">or click to browse</p>
                    </div>
                  )}
                </div>
              )}

              {/* Layout selector */}
              <div className="space-y-1.5">
                <label className="text-xs uppercase tracking-wider text-text-gray">Graph Layout</label>
                <select value={layout} onChange={e => setLayout(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-[12px] p-2.5 text-sm text-white focus:outline-none focus:border-primary-cyan transition-colors">
                  <option value="dagre">Hierarchical Flow (Top-Bottom)</option>
                  <option value="dagre-lr">Hierarchical Flow (Left-Right)</option>
                  <option value="cose">Force-Directed (Balanced)</option>
                  <option value="circle">Circular</option>
                  <option value="grid">Grid</option>
                </select>
              </div>

              {/* Generate button */}
              <button onClick={handleGenerate} disabled={loading}
                className="w-full flex items-center justify-center gap-2.5 py-3.5 rounded-[16px] bg-primary-cyan text-black font-semibold hover:bg-primary-cyan/80 transition-all disabled:opacity-50">
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Generating..." : "Generate Mind-Map"}
              </button>
            </div>

            {/* Stats card */}
            {stats && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="bg-card-bg border border-card-border rounded-[28px] p-5 space-y-3">
                <div className="flex items-center gap-2 text-primary-cyan">
                  <BarChart2 className="w-4 h-4" />
                  <span className="text-sm font-semibold">Graph Statistics</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {[["Concepts", stats.nodes, "text-primary-cyan"], ["Connections", stats.edges, "text-accent-teal"], ["Most Linked", stats.topNode, "text-purple-400"], ["Main Topic", stats.types.central, "text-amber-400"]].map(([k, v, c]) => (
                    <div key={k} className="bg-black/30 rounded-[12px] p-3">
                      <p className="text-xs text-text-gray">{k}</p>
                      <p className={`text-lg font-bold mt-0.5 ${c} truncate`}>{v}</p>
                    </div>
                  ))}
                </div>
                {/* Type breakdown */}
                <div className="space-y-1.5 pt-1">
                  {LEGEND.map(({ type, label, color }) => stats.types[type] > 0 && (
                    <div key={type} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                        <span className="text-xs text-text-gray">{label}</span>
                      </div>
                      <span className="text-xs font-semibold" style={{ color }}>{stats.types[type]}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Node detail card */}
            <AnimatePresence>
              {selected && (
                <motion.div key={selected.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
                  className="bg-card-bg border border-card-border rounded-[28px] p-5 space-y-3">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-white/50" />
                    <span className="text-sm font-semibold">Concept Details</span>
                    <button onClick={() => setSelected(null)} className="ml-auto text-white/30 hover:text-white">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div>
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs border font-medium mb-2 ${typeBadge(selected.type)}`}>
                      {selected.type}
                    </span>
                    <p className="text-lg font-bold leading-snug">{selected.label}</p>
                  </div>
                  {selected.description && (
                    <p className="text-sm text-text-gray leading-relaxed">{selected.description}</p>
                  )}
                  <div className="flex gap-3 text-xs text-text-gray">
                    <span>↑ {selected.incoming.length} incoming</span>
                    <span>↓ {selected.outgoing.length} outgoing</span>
                    <span>Degree: {selected.degree}</span>
                  </div>
                  {(selected.incoming.length > 0 || selected.outgoing.length > 0) && (
                    <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1">
                      {selected.incoming.map((e, i) => (
                        <div key={`in-${i}`} className="bg-black/30 rounded-[10px] px-3 py-2 text-xs">
                          <span className="text-primary-cyan font-medium">{e.from}</span>
                          <span className="text-text-gray mx-1.5">—{e.label}→</span>
                          <span className="text-white font-medium">{selected.label}</span>
                        </div>
                      ))}
                      {selected.outgoing.map((e, i) => (
                        <div key={`out-${i}`} className="bg-black/30 rounded-[10px] px-3 py-2 text-xs">
                          <span className="text-white font-medium">{selected.label}</span>
                          <span className="text-text-gray mx-1.5">—{e.label}→</span>
                          <span className="text-accent-teal font-medium">{e.to}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ── Right: Graph ── */}
          <div className="lg:col-span-8 flex flex-col">
            <div className="bg-card-bg border border-card-border rounded-[28px] p-4 flex flex-col flex-1 min-h-[640px] relative">

              {/* Floating toolbar */}
              {elements && (
                <>
                  {/* Zoom controls */}
                  <div className="absolute top-5 left-5 z-10 flex flex-col gap-2">
                    {[[ZoomIn, zoomIn, "Zoom In"], [ZoomOut, zoomOut, "Zoom Out"], [Maximize2, fitView, "Fit View"], [Download, exportPng, "Export PNG"]].map(([Icon, fn, tip]) => (
                      <button key={tip} onClick={fn} title={tip}
                        className="p-2.5 bg-black/70 backdrop-blur-md border border-white/10 hover:border-primary-cyan rounded-[12px] text-white/60 hover:text-primary-cyan transition-all">
                        <Icon className="w-4 h-4" />
                      </button>
                    ))}
                  </div>

                  {/* Search bar */}
                  <div className="absolute top-5 right-5 z-10 flex items-center gap-2 bg-black/70 backdrop-blur-md border border-white/10 rounded-[14px] px-3 py-2">
                    <Search className="w-3.5 h-3.5 text-text-gray shrink-0" />
                    <input value={search} onChange={e => setSearch(e.target.value)}
                      placeholder="Search concept..."
                      className="bg-transparent text-sm text-white placeholder-text-gray focus:outline-none w-36" />
                    {search && <button onClick={() => setSearch("")}><X className="w-3 h-3 text-text-gray hover:text-white" /></button>}
                  </div>

                  {/* Legend */}
                  <div className="absolute bottom-6 right-5 z-10 bg-black/70 backdrop-blur-md border border-white/10 rounded-[14px] px-4 py-3 space-y-1.5">
                    {LEGEND.map(({ label, color }) => (
                      <div key={label} className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                        <span className="text-xs text-text-gray">{label}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Cytoscape container */}
              <div ref={containerRef} id="cy" className="w-full flex-1 rounded-[20px] bg-black/20 overflow-hidden" style={{ minHeight: 580 }} />

              {/* Empty state */}
              {!elements && !loading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 pointer-events-none">
                  <Network className="w-16 h-16 text-white/10 mb-4" />
                  <p className="font-semibold text-white/40">Your mind-map will appear here</p>
                  <p className="text-xs text-text-gray mt-1 max-w-xs">Paste notes or upload a PDF, then click Generate</p>
                </div>
              )}

              {/* Loading overlay */}
              {loading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm rounded-[24px] z-20">
                  <div className="relative w-14 h-14">
                    <div className="absolute inset-0 rounded-full border-4 border-primary-cyan/20" />
                    <div className="absolute inset-0 rounded-full border-4 border-t-primary-cyan animate-spin" />
                  </div>
                  <p className="font-semibold text-white mt-5">Extracting Concepts</p>
                  <p className="text-xs text-text-gray mt-1">AI is analyzing your notes...</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
