import "./Skeleton.css";

export default function Skeleton({ width = "100%", height = 12, style, className = "" }) {
  return (
    <div
      className={`ns-skel${className ? " " + className : ""}`}
      style={{ width, height, ...style }}
    />
  );
}
