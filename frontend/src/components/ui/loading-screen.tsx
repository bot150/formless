import "./loading-screen.css";

export default function LoadingScreen() {
  return (
    <div className="formless-loader">
      <div className="loader-pill">
        <span className="loader-dot loader-dot-1" />
        <span className="loader-dot loader-dot-2" />
        <span className="loader-dot loader-dot-3" />
        <span className="loader-dot loader-dot-4" />
      </div>
    </div>
  );
}