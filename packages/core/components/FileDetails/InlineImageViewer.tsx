import * as React from "react";

interface PreviewMeta {
    z_count: number;
    c_count: number;
    channel_names: string[];
    preview_base: string;
    filename: string;
}

interface Props {
    previewUrl: string;
}

/**
 * Inline channel / Z-plane image viewer, shown in the file details panel.
 * Reads meta.json from the previewUrl query param, then lets the user
 * flip through channels and Z-planes without leaving the app.
 */
export default function InlineImageViewer({ previewUrl }: Props) {
    const [meta, setMeta] = React.useState<PreviewMeta | null>(null);
    const [z, setZ] = React.useState(0);
    const [c, setC] = React.useState(0);
    const [imgSrc, setImgSrc] = React.useState("");
    const [loading, setLoading] = React.useState(false);

    const metaUrl = React.useMemo(() => {
        try {
            return new URLSearchParams(previewUrl.split("?")[1] || "").get("meta") || "";
        } catch {
            return "";
        }
    }, [previewUrl]);

    // Fetch metadata once per file
    React.useEffect(() => {
        if (!metaUrl) return;
        setMeta(null);
        fetch(metaUrl)
            .then((r) => r.json())
            .then((data: PreviewMeta) => {
                setMeta(data);
                setZ(Math.floor((data.z_count || 1) / 2));
                setC(0);
            })
            .catch(() => setMeta(null));
    }, [metaUrl]);

    // Preload next image when z or c change
    React.useEffect(() => {
        if (!meta) return;
        const src = `${meta.preview_base}.c${c}.z${String(z).padStart(3, "0")}.jpg`;
        setLoading(true);
        const img = new window.Image();
        img.onload = () => {
            setImgSrc(src);
            setLoading(false);
        };
        img.onerror = () => {
            setImgSrc(src);
            setLoading(false);
        };
        img.src = src;
    }, [meta, z, c]);

    if (!meta) return null;

    const btnBase: React.CSSProperties = {
        padding: "2px 10px",
        fontSize: 12,
        border: "1px solid",
        borderRadius: 3,
        cursor: "pointer",
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
            {/* Channel selector */}
            <div
                style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 4,
                    marginBottom: 6,
                    flexShrink: 0,
                }}
            >
                {Array.from({ length: meta.c_count }, (_, i) => (
                    <button
                        key={i}
                        onClick={() => setC(i)}
                        style={{
                            ...btnBase,
                            borderColor: c === i ? "#1d4ed8" : "#444",
                            background: c === i ? "#1d4ed8" : "#2a2a2a",
                            color: c === i ? "#fff" : "#ccc",
                        }}
                    >
                        {meta.channel_names[i] || `Ch ${i + 1}`}
                    </button>
                ))}
            </div>

            {/* Image — fills remaining height, letterboxed */}
            <div
                style={{
                    flex: 1,
                    minHeight: 0,
                    background: "#000",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden",
                }}
            >
                <img
                    src={imgSrc}
                    alt=""
                    style={{
                        maxWidth: "100%",
                        maxHeight: "100%",
                        objectFit: "contain",
                        display: "block",
                        opacity: loading ? 0.5 : 1,
                        transition: "opacity 0.1s",
                    }}
                />
            </div>

            {/* Z slider */}
            {meta.z_count > 1 && (
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginTop: 6,
                        flexShrink: 0,
                    }}
                >
                    <span style={{ fontSize: 11, color: "#888", minWidth: 42 }}>Z-plane</span>
                    <input
                        type="range"
                        min={0}
                        max={meta.z_count - 1}
                        value={z}
                        onChange={(e) => setZ(+e.target.value)}
                        style={{ flex: 1, accentColor: "#1d4ed8", cursor: "pointer" }}
                    />
                    <span style={{ fontSize: 11, color: "#888", minWidth: 40, textAlign: "right" }}>
                        {z + 1} / {meta.z_count}
                    </span>
                </div>
            )}
        </div>
    );
}
