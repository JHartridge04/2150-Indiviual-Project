import React, { useState } from "react";
import { Link } from "react-router-dom";
import "./Landing.css";

const SCREENSHOTS = [
  { src: "/landing-screenshots/01-upload.png",  alt: "Upload page" },
  { src: "/landing-screenshots/02-analyze.png", alt: "Style analysis result" },
  { src: "/landing-screenshots/03-shop.png",    alt: "Product recommendations" },
];

function ScreenshotSlot({ src, alt, fallbackLabel }) {
  const [failed, setFailed] = useState(false);

  const handleError = () => {
    console.error(`[Landing] Screenshot not found: ${src}`);
    setFailed(true);
  };

  return (
    <div className="screenshot-slot">
      {!failed ? (
        <img
          className="screenshot-img"
          src={src}
          alt={alt}
          onError={handleError}
        />
      ) : (
        <div className="screenshot-inner">
          <div className="screenshot-label">{fallbackLabel}</div>
        </div>
      )}
    </div>
  );
}

function TickRuler() {
  const ticks = [
    { lg: true }, {}, {}, {}, { lg: true }, {}, {}, {}, { lg: true },
    {}, {}, {}, { lg: true }, {}, {}, {}, { lg: true },
  ];
  return (
    <div className="tick-ruler">
      {ticks.map((t, i) => (
        <React.Fragment key={i}>
          <span
            className={`tick${t.lg ? " tick-lg" : ""}`}
            style={{ width: t.lg ? "14px" : "8px" }}
          />
          {i < ticks.length - 1 && <span style={{ display: "block", height: "9px" }} />}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function Landing() {
  const today = new Date();
  const dateStr = `${today.getFullYear()}.${String(today.getMonth() + 1).padStart(2, "0")}.${String(today.getDate()).padStart(2, "0")}`;

  return (
    <div className="landing">

      {/* ═══ § 1 · HERO ═══════════════════════════════════════ */}
      <section className="landing-hero" id="hero">
        <div className="hero-topbar">
          <span className="mono">
            SYS/01 <span className="mono-accent">·</span> v1.0{" "}
            <span className="mono-accent">·</span> 2026
          </span>
          <span className="mono">{dateStr}</span>
        </div>

        <div className="hero-body">
          <div className="hero-ruler" aria-hidden="true">
            <TickRuler />
            <div className="ruler-section-label">01 / HERO</div>
          </div>

          <div className="hero-content">
            <div className="hero-wordmark">
              NO<br />STYLIST
            </div>

            <div className="hero-tagline">
              AI-POWERED PERSONAL STYLE. NO GATEKEEPING.
            </div>

            <p className="hero-blurb">
              Upload, analyze, build outfits, shop the gaps.<br />
              Your wardrobe and your style — audited by AI,<br />
              never by strangers.
            </p>

            <div className="hero-cta-row">
              <Link to="/signup" className="btn-primary">
                ENTER <span className="arr">→</span>
              </Link>
              <Link to="/login" className="btn-ghost">
                Already have an account? Sign in
              </Link>
            </div>
          </div>
        </div>

        <div className="hero-bottombar">
          <span className="mono">01 / HERO</span>
          <a href="#spec" className="scroll-label">
            <span className="scroll-arrow">↓</span> SCROLL FOR SPEC
          </a>
        </div>
      </section>

      {/* ═══ § 2 · THE SPEC ════════════════════════════════════ */}
      <section className="landing-spec" id="spec">
        <div className="spec-header">
          <div>
            <div className="eyebrow">02 / CAPABILITIES</div>
            <div className="section-heading">THE SPEC</div>
          </div>
          <div className="spec-header-meta">
            <div>4 CORE MODULES</div>
            <div className="spec-header-meta-row">
              <span className="dot" style={{ width: "5px", height: "5px" }} />
              <span>HOVER TO INSPECT</span>
            </div>
          </div>
        </div>

        <div className="spec-grid">
          <div className="spec-block">
            <div className="spec-glyph">01</div>
            <div className="spec-num">
              <span className="dot" /> 01 / STYLE ANALYSIS
            </div>
            <div className="spec-title">Style<br />Analysis</div>
            <div className="spec-desc">
              AI vision reads your outfit and returns colours, silhouettes, style tags,
              and a full written review. Every upload becomes a data point in your
              evolving style profile.
            </div>
          </div>

          <div className="spec-block">
            <div className="spec-glyph">02</div>
            <div className="spec-num">
              <span className="dot" /> 02 / WARDROBE AUDIT
            </div>
            <div className="spec-title">Wardrobe<br />Audit</div>
            <div className="spec-desc">
              Upload your closet. AI identifies category gaps, clustering your items
              by style DNA and surfacing the exact pieces you're missing — with
              shoppable fills.
            </div>
          </div>

          <div className="spec-block">
            <div className="spec-glyph">03</div>
            <div className="spec-num">
              <span className="dot" /> 03 / OUTFIT BUILDER
            </div>
            <div className="spec-title">Outfit<br />Builder</div>
            <div className="spec-desc">
              Pick an anchor piece. AI assembles the rest from your wardrobe and
              fills missing gaps with real products sourced in real time. One item
              becomes a full look.
            </div>
          </div>

          <div className="spec-block">
            <div className="spec-glyph">04</div>
            <div className="spec-num">
              <span className="dot" /> 04 / GENERATE A LOOK
            </div>
            <div className="spec-title">Generate<br />A Look</div>
            <div className="spec-desc">
              Tell it the occasion, weather, and vibe. It designs the full outfit —
              pulling from your wardrobe first and sourcing anything you don't own
              from across the web.
            </div>
          </div>
        </div>
      </section>

      {/* ═══ § 3 · HOW IT WORKS ════════════════════════════════ */}
      <section className="landing-process" id="process">
        <div className="process-header">
          <div className="eyebrow">03 / PROCESS</div>
          <div className="section-heading">How It Works</div>
        </div>

        <div className="process-body">
          <div className="process-track" aria-hidden="true">
            <div className="track-tick" style={{ left: "33.3%" }} />
            <div className="track-tick" style={{ left: "66.6%" }} />
          </div>

          <div className="process-steps">
            <div className="step">
              <div className="step-numeral">01</div>
              <div className="step-label">Upload</div>
              <div className="step-desc">
                Upload a photo of your outfit or your entire wardrobe. Batch
                uploads supported. AI does the rest.
              </div>
              <ScreenshotSlot {...SCREENSHOTS[0]} fallbackLabel="Upload Page" />
            </div>

            <div className="step">
              <div className="step-numeral">02</div>
              <div className="step-label">Analyze</div>
              <div className="step-desc">
                AI reads the style, tags it, writes a review, and builds your
                evolving style profile automatically.
              </div>
              <ScreenshotSlot {...SCREENSHOTS[1]} fallbackLabel="Style Profile Output" />
            </div>

            <div className="step">
              <div className="step-numeral">03</div>
              <div className="step-label">Shop</div>
              <div className="step-desc">
                Get real products to complete your look. AI cross-references your
                style profile and sources items from across the web.
              </div>
              <ScreenshotSlot {...SCREENSHOTS[2]} fallbackLabel="Recommendations Page" />
            </div>
          </div>
        </div>
      </section>

      {/* ═══ § 4 · CTA FOOTER ══════════════════════════════════ */}
      <section className="landing-enter" id="enter">
        <div className="enter-body">
          <div className="enter-eyebrow">
            <span className="dot" />
            04 / ENTER
            <span className="dot" />
          </div>

          <div className="enter-heading">READY?</div>

          <p className="enter-subtext">
            Sign up. Upload. Stop asking other people how to dress.
          </p>

          <div className="enter-cta-row">
            <Link to="/signup" className="btn-primary-inv">
              CREATE ACCOUNT <span className="arr">→</span>
            </Link>
            <Link to="/login" className="btn-ghost-inv">Sign in</Link>
          </div>
        </div>

        <div className="enter-footer">
          <span>SYS/01</span>
          <span className="dot" />
          <span>NO STYLIST</span>
          <span className="dot" />
          <span>EST. 2026</span>
        </div>
      </section>

    </div>
  );
}
