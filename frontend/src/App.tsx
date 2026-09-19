import "./App.css";

function App() {
  return (
    <main className="formless-page">
      <section className="hero">

        {/* Top navigation */}
        <header className="top-bar">
          <div className="brand">formless.</div>

          <div className="category">
            Forms · digital experiences
          </div>
        </header>

        {/* Hero content */}
        <div className="hero-content">

          <p className="eyebrow">
            Forms, reimagined.
          </p>

          <h1 className="logo" aria-label="formless">
            {"formless".split("").map((letter, index) => (
              <span key={index}>{letter}</span>
            ))}
          </h1>

          <p className="subtitle">
            Tell us what you know. We'll handle the rest.
          </p>

          <button className="start-button">
            <span>Start filling</span>
            <span className="arrow">↘</span>
          </button>

        </div>

      </section>
    </main>
  );
}

export default App;