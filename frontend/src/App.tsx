import { useEffect, useState } from "react";
import ShinyButton from "./components/ui/shiny-button";
import GlyphPortal from "./components/ui/glyph-portal";
import LoadingScreen from "./components/ui/loading-screen";
import "./App.css";

function App() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(false);
    }, 2800);

    return () => {
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <>
      {loading && <LoadingScreen />}

      <main className="formless-page">
        <GlyphPortal
          word="formless"
          interactive={true}
          scrollLength={4}
          fontFamily="Arial, Helvetica, sans-serif"
          fontWeight={700}
          enterLabel="Scroll to enter"
          style={{
            "--gp-paper": "#f8f4f0",
            "--gp-ink": "#6b1f2b",
            "--gp-field": "#6b1f2b",
            "--gp-foreground": "#f8f4f0",
          }}
          front={
            <div className="formless-hero">
              <header className="top-bar">
                <div className="brand">
                  formless.
                </div>

                <div className="category">
                  Forms · digital experiences
                </div>
              </header>

              <div className="hero-copy">
                <p className="eyebrow">
                  Forms, reimagined.
                </p>

                <p className="subtitle">
                  Tell us what you know. We'll handle the rest.
                </p>

                <div className="hero-button">
                  <ShinyButton
                    label="Start filling  ↘"
                    fillColor="#6b1f2b"
                    labelColor="#f8f4f0"
                    accentColor="#f8f4f0"
                    accentSoftColor="#c98f98"
                    cornerRadius={12}
                  />
                </div>
              </div>
            </div>
          }
        >
          <section className="formless-content">
            <div className="content-inner">
              <p className="content-eyebrow">
                Welcome to Formless.
              </p>

              <h2>
                Tell us what
                <br />
                you know.
              </h2>

              <p className="content-description">
                Answer a few simple questions. We'll take care of
                the rest and turn your responses into a seamless
                digital experience.
              </p>

              <button className="content-button">
                Start filling
                <span>↘</span>
              </button>
            </div>
          </section>
        </GlyphPortal>
      </main>
    </>
  );
}

export default App;